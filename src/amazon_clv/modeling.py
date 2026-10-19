"""Bounded chronological model selection and a portable two-horizon bundle."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from .features import feature_columns, training_rows
from .metrics import evaluate

def candidate_specs():
    specs = [{"name":"trailing_90","kind":"baseline","days":90,"complexity":0},
             {"name":"trailing_365","kind":"baseline","days":365,"complexity":1}]
    specs += [{"name":f"ridge_{a:g}","kind":"ridge","alpha":a,"complexity":2} for a in [.1,1,10,100]]
    specs += [{"name":f"hgb_{lr:g}_{leaves}","kind":"hgb","learning_rate":lr,"max_leaf_nodes":leaves,"complexity":3} for lr in [.05,.1] for leaves in [15,31]]
    return specs

@dataclass
class SpendingModel:
    spec: dict
    horizon: int
    columns: list[str]
    estimator: object = None

    def fit(self, frame):
        if len(frame) == 0:
            raise ValueError("No fully observed training examples before cutoff")
        if self.spec["kind"] == "ridge":
            self.estimator = make_pipeline(StandardScaler(), Ridge(alpha=self.spec["alpha"]))
        elif self.spec["kind"] == "hgb":
            self.estimator = HistGradientBoostingRegressor(learning_rate=self.spec["learning_rate"], max_leaf_nodes=self.spec["max_leaf_nodes"],max_iter=300,early_stopping=False,random_state=42)
        if self.estimator is not None:
            self.estimator.fit(frame[self.columns],frame[f"target_{self.horizon}"])
        return self

    def predict(self, frame):
        if self.spec["kind"] == "baseline":
            p = frame[f"spend_{self.spec['days']}"] * self.horizon / self.spec["days"]
        else:
            p = self.estimator.predict(frame[self.columns])
        return np.maximum(0,np.asarray(p,float))

@dataclass
class ModelBundle:
    categories: list[str]
    models: dict[int, SpendingModel]
    version: str
    training_cutoff: str = "2022-01-01"
    observation_end: str = "2022-11-01"

    def predict(self, snapshot):
        p90 = self.models[90].predict(snapshot)
        raw180 = self.models[180].predict(snapshot)
        return {90:p90,180:np.maximum(raw180,p90)}, raw180 < p90, raw180

def choose_candidate(summary):
    """1% RMSE band, capture tie-break, then complexity. ML must beat best baseline RMSE."""
    baseline = summary.loc[summary.kind.eq("baseline"),"mean_rmse"].min()
    eligible = summary.loc[summary.kind.eq("baseline") | summary.mean_rmse.lt(baseline)].copy()
    eligible = eligible.loc[eligible.mean_rmse <= eligible.mean_rmse.min()*1.01]
    # Capture is compared before complexity as specified. Deterministic final name tie.
    return eligible.sort_values(["mean_capture_20","complexity","mean_rmse","name"],ascending=[False,True,True,True]).iloc[0]["name"]

def validate_models(snapshots):
    cols = feature_columns(snapshots)
    specs = candidate_specs()
    folds = [pd.Timestamp("2021-01-01"),pd.Timestamp("2021-07-01")]
    rows, split_rows, winners, validation_preds = [], [], {}, []
    anchor_predictions = {}
    for horizon in [90,180]:
        pred_cache = {}
        for fold in folds:
            train = training_rows(snapshots,horizon,fold,development_only=True)
            val = snapshots.loc[snapshots.scoring_date.eq(fold)].sort_values("customer_id").copy()
            split_rows.append({"stage":"validation","horizon":horizon,"cutoff":str(fold.date()),"train_n":len(train),"max_train_scoring_date":str(train.scoring_date.max().date()),"max_label_end":str(train[f"label_end_{horizon}"].max().date()),"validation_n":len(val),"category_fit_end_exclusive":"2019-01-01"})
            for spec in specs:
                print(f"validation {horizon}d {fold.date()} {spec['name']} ({len(train):,} examples)",flush=True)
                model = SpendingModel(spec,horizon,cols).fit(train)
                raw = model.predict(val)
                p = np.maximum(raw,anchor_predictions[fold]) if horizon==180 else raw
                row = {"horizon":horizon,"scoring_date":str(fold.date()),**spec,**evaluate(val[f"target_{horizon}"],p),"adjustment_rate":float(np.mean(p!=raw))}
                rows.append(row)
                pred_cache[(fold,spec["name"])] = (val,raw,p)
        table = pd.DataFrame([r for r in rows if r["horizon"]==horizon])
        summary = table.groupby(["name","kind","complexity"],as_index=False).agg(mean_rmse=("rmse","mean"),mean_capture_20=("capture_20","mean"))
        winner = choose_candidate(summary)
        winners[horizon] = next(s for s in specs if s["name"]==winner)
        print(f"SELECTED {horizon}d: {winner}",flush=True)
        for fold in folds:
            val,raw,p = pred_cache[(fold,winner)]
            if horizon==90:
                anchor_predictions[fold] = p
            f = pd.DataFrame({"customer_id":val.customer_id.to_numpy(),"scoring_date":str(fold.date()),"horizon":horizon,"predicted_spending":p,"raw_predicted_spending":raw,"actual_spending":val[f"target_{horizon}"].to_numpy(),"historical_score":val.spend_365.to_numpy()})
            validation_preds.append(f)
    return winners,pd.DataFrame(rows),pd.DataFrame(split_rows),pd.concat(validation_preds,ignore_index=True)
