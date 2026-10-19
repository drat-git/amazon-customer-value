"""Complete analytical pipeline: audit, snapshot, validate, freeze, evaluate, export."""
from __future__ import annotations
import json
import platform
import time
from pathlib import Path
from datetime import datetime, timezone
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from .data import load_transactions
from .features import fit_category_map, make_snapshot, feature_columns, training_rows
from .modeling import SpendingModel, ModelBundle, candidate_specs, validate_models
from .metrics import evaluate, calibration, bootstrap, capture
from .marketing import compare_audiences

def save_json(path, obj):
    Path(path).write_text(json.dumps(obj,indent=2,default=str)+"\n")

def predict_export(bundle, snapshot):
    pred,changed,raw180 = bundle.predict(snapshot)
    rows=[]
    for h in [90,180]:
        f = snapshot[["customer_id","scoring_date","recency_days","history_days","spend_365","spend_90","purchase_days_365"]].copy()
        f = f.rename(columns={"spend_365":"historical_score"})
        f["horizon"]=h
        f["predicted_spending"]=pred[h]
        f["raw_predicted_spending"]=raw180 if h==180 else pred[h]
        f["coherence_adjusted"]=changed if h==180 else False
        f["actual_spending"]=snapshot.get(f"target_{h}",pd.Series(np.nan,index=snapshot.index))
        f["model_name"]=bundle.models[h].spec["name"]
        f["model_version"]=bundle.version
        f["segment"]=np.select([f.history_days.lt(90),f.recency_days.ge(180)],["Short history","Inactive"],default="Established")
        rows.append(f)
    return pd.concat(rows,ignore_index=True)

def _analysis(tx, out, version, n_bootstrap):
    out.mkdir(parents=True,exist_ok=True)
    (out/"bundle").mkdir(exist_ok=True)
    categories=fit_category_map(tx)
    save_json(out/"category_mapping.json",{"fit_end_exclusive":"2019-01-01","categories":categories+["UNKNOWN","OTHER"],"feature_names":[f"category_share_{i:02}" for i in range(len(categories)+2)]})
    snapshots=[]
    for d in pd.date_range("2019-01-01","2022-10-01",freq="MS"):
        print(f"snapshot {d.date()}",flush=True)
        snapshots.append(make_snapshot(tx,d,categories))
    snapshots=pd.concat(snapshots,ignore_index=True)
    snapshots.to_parquet(out/"snapshots.parquet",index=False)
    winners,val_metrics,splits,val_predictions=validate_models(snapshots)
    val_metrics.to_csv(out/"validation_metrics.csv",index=False)
    val_predictions.to_csv(out/"validation_predictions.csv",index=False)
    save_json(out/"frozen_selection.json",{"selected":winners,"selection_rule":"90 first; 180 evaluated after max(raw180, selected90). Equal fold weighting. 1% RMSE band then capture, then simplicity. ML must improve best baseline RMSE.","frozen_before_test":True})
    # All candidates use the same labels available before 2022, with no test refitting.
    fitted={}
    split_records=splits.to_dict("records")
    for h in [90,180]:
        train=training_rows(snapshots,h,"2022-01-01")
        split_records.append({"stage":"final_fit","horizon":h,"cutoff":"2022-01-01","train_n":len(train),"max_label_end":str(train[f"label_end_{h}"].max().date()),"max_train_scoring_date":str(train.scoring_date.max().date()),"category_fit_end_exclusive":"2019-01-01"})
        for spec in candidate_specs():
            print(f"final fit {h}d {spec['name']}",flush=True)
            fitted[(h,spec["name"])]=SpendingModel(spec,h,feature_columns(snapshots)).fit(train)
    pd.DataFrame(split_records).to_csv(out/"split_audit.csv",index=False)
    bundle=ModelBundle(categories,{h:fitted[(h,winners[h]["name"])] for h in [90,180]},version)
    joblib.dump(bundle,out/"bundle"/"models.joblib")
    save_json(out/"bundle"/"manifest.json",{"model_version":version,"training_cutoff":"2022-01-01","observation_end_exclusive":"2022-11-01","models":winners,"feature_columns":feature_columns(snapshots),"categories":categories,"python":platform.python_version()})
    test=snapshots.loc[snapshots.scoring_date.isin(pd.to_datetime(["2022-01-01","2022-05-01"]))].copy()
    predictions=predict_export(bundle,test)
    predictions.to_csv(out/"customer_predictions.csv",index=False,float_format="%.10f")
    predictions.to_parquet(out/"customer_predictions.parquet",index=False)
    metrics,calibrations,segment_rows,marketing_rows=[],[],[],[]
    for (h,d),f in predictions.groupby(["horizon","scoring_date"],sort=True):
        snapshot=test.loc[test.scoring_date.eq(d)].copy()
        anchor=bundle.models[90].predict(snapshot)
        for spec in candidate_specs():
            raw=fitted[(h,spec["name"])].predict(snapshot)
            p=np.maximum(raw,anchor) if h==180 else raw
            result=evaluate(snapshot[f"target_{h}"],p)
            historical_capture_10=capture(snapshot[f"target_{h}"],snapshot.spend_365,.1)
            historical_capture_20=capture(snapshot[f"target_{h}"],snapshot.spend_365,.2)
            metrics.append({"horizon":h,"scoring_date":str(d.date()),"model":spec["name"],"selected":spec["name"]==winners[h]["name"],"adjustment_rate":float(np.mean(p!=raw)),**result,"historical_capture_10":historical_capture_10,"historical_capture_20":historical_capture_20,"capture_10_gain_pp":100*(result["capture_10"]-historical_capture_10),"capture_20_gain_pp":100*(result["capture_20"]-historical_capture_20)})
        cal=calibration(f)
        cal["horizon"],cal["scoring_date"]=h,str(d.date())
        calibrations.append(cal)
        masks={"All customers":pd.Series(True,index=f.index),"Low history (<90 days)":f.history_days.lt(90),"Inactive (>=180 days)":f.recency_days.ge(180),"High historical spending (top 10%)":f.historical_score.ge(f.historical_score.quantile(.9))}
        for name,mask in masks.items():
            if mask.any():
                segment_rows.append({"horizon":h,"scoring_date":str(d.date()),"segment":name,**evaluate(f.loc[mask,"actual_spending"],f.loc[mask,"predicted_spending"])})
        market,selected=compare_audiences(f)
        market["horizon"],market["scoring_date"]=h,str(d.date())
        marketing_rows.append(market)
        selected.to_csv(out/f"audience_{d.date()}_{h}.csv",index=False)
    pd.DataFrame(metrics).to_csv(out/"test_metrics.csv",index=False)
    pd.concat(calibrations).to_csv(out/"calibration.csv",index=False)
    pd.DataFrame(segment_rows).to_csv(out/"segment_errors.csv",index=False)
    pd.concat(marketing_rows).to_csv(out/"marketing_comparison.csv",index=False)
    intervals=[]
    for h in [90,180]:
        f=predictions.loc[predictions.horizon.eq(h)]
        for scope,part in [("Both test dates",f)]+[(str(d.date()),g) for d,g in f.groupby("scoring_date")]:
            print(f"bootstrap {h}d {scope} ({n_bootstrap} customer resamples)",flush=True)
            intervals.extend({"horizon":h,"scope":scope,**r} for r in bootstrap(part,n_bootstrap))
    pd.DataFrame(intervals).to_csv(out/"bootstrap_intervals.csv",index=False)
    # Deterministic permutation explanation only after selection and test prediction.
    # These associations never feed model selection. Evaluate raw model outputs.
    from sklearn.inspection import permutation_importance
    importance=[]
    sample=test.loc[test.scoring_date.eq(pd.Timestamp("2022-01-01"))].sample(n=min(1500,int(test.scoring_date.eq(pd.Timestamp("2022-01-01")).sum())),random_state=42)
    for h in [90,180]:
        model=bundle.models[h]
        if model.estimator is not None:
            imp=permutation_importance(model.estimator,sample[model.columns],sample[f"target_{h}"],scoring="neg_root_mean_squared_error",n_repeats=3,random_state=42)
            importance.extend({"horizon":h,"feature":c,"rmse_increase":m,"std":s} for c,m,s in zip(model.columns,imp.importances_mean,imp.importances_std))
        else:
            importance.append({"horizon":h,"feature":f"spend_{model.spec['days']}","rmse_increase":np.nan,"std":np.nan})
    pd.DataFrame(importance).to_csv(out/"predictive_associations.csv",index=False)
    return predictions,pd.DataFrame(metrics),bundle

def run(data,output,verify_source=True,n_bootstrap=500,sensitivity=True):
    start=time.perf_counter()
    out=Path(output).resolve()
    if (out/"manifest.json").exists():
        raise ValueError("Output already contains a completed run. Choose a new directory to preserve the evaluation record.")
    out.mkdir(parents=True,exist_ok=True)
    print("Auditing source and normalizing transactions",flush=True)
    tx,audit=load_transactions(data,verify_source=verify_source)
    save_json(out/"data_audit.json",audit)
    tx.to_parquet(out/"transactions.parquet",index=False)
    version="amazon-clv-1.0-"+audit["sha256"][:10]
    with threadpool_limits(limits=4):
        predictions,metrics,bundle=_analysis(tx,out,version,n_bootstrap)
        if sensitivity:
            p2,m2,_=_analysis(tx.loc[~tx.is_gift].copy(),out/"no_gift_cards",version+"-no-gifts",n_bootstrap)
            comparison=pd.concat([metrics.loc[metrics.selected].assign(analysis="Primary (gift cards retained)"),m2.loc[m2.selected].assign(analysis="Sensitivity (gift cards excluded)")],ignore_index=True)
            comparison.to_csv(out/"gift_sensitivity.csv",index=False)
    manifest={"run_version":version,"completed_utc":datetime.now(timezone.utc).isoformat(),"seed":42,"bootstrap_resamples":n_bootstrap,"source_md5":audit["md5"],"source_sha256":audit["sha256"],"sensitivity_completed":sensitivity,"elapsed_seconds":time.perf_counter()-start,"notes":"Both test dates use the same final bundle. Overlapping windows and repeated customers are dependent. Bootstrap resamples customers, conditional on fitted models."}
    save_json(out/"manifest.json",manifest)
    from .charts import build_charts
    build_charts(out)
    print(f"Completed analytical run in {manifest['elapsed_seconds']:.1f}s: {out}",flush=True)
    return out
