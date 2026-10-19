import io
import joblib
import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal
from amazon_clv.features import make_snapshot,fit_category_map,feature_columns,training_rows
from amazon_clv.modeling import SpendingModel,ModelBundle,candidate_specs,choose_candidate
from amazon_clv.pipeline import predict_export
from amazon_clv.marketing import capacity,select_audience,compare_audiences,export_selection
from amazon_clv.metrics import bootstrap
from amazon_clv.data import load_transactions

def test_future_cannot_change_features(transactions):
    a=make_snapshot(transactions,"2019-01-01",["BOOK"])
    altered=pd.concat([transactions,pd.DataFrame([{**transactions.iloc[0].to_dict(),"date":pd.Timestamp("2020-01-01"),"value_cents":99999999,"category":"FUTURE"}])],ignore_index=True)
    b=make_snapshot(altered,"2019-01-01",["BOOK"])
    assert_frame_equal(a[["customer_id"]+feature_columns(a)],b[["customer_id"]+feature_columns(b)])

def test_exact_date_is_target_and_zero_outcomes_stay(transactions):
    s=make_snapshot(transactions,"2019-01-01",["BOOK"]).set_index("customer_id")
    assert list(s.index)==["a","b"]
    assert s.loc["a","lifetime_spend"]==100
    assert s.loc["a","target_90"]==50
    assert s.loc["b","target_90"]==0
    assert s.loc["b","recency_days"]==1

def test_right_endpoint_excluded(transactions):
    s=make_snapshot(transactions,"2019-01-01",[],observation_end="2019-04-01")
    end=pd.Timestamp("2019-01-01")+pd.Timedelta(days=90)
    extra={**transactions.iloc[0].to_dict(),"date":end,"value_cents":100000}
    later=make_snapshot(pd.concat([transactions,pd.DataFrame([extra])]),"2019-01-01",[],observation_end="2019-04-01")
    np.testing.assert_array_equal(s.target_90,later.target_90)

def test_unobserved_targets_are_nan(transactions):
    s=make_snapshot(transactions,"2019-01-01",[],observation_end="2019-04-01")
    assert s.target_90.notna().all()
    assert s.target_180.isna().all()

def test_purge_labels(transactions):
    s=pd.concat([make_snapshot(transactions,d,[]) for d in pd.date_range("2019-01-01","2019-06-01",freq="MS")])
    for h in [90,180]:
        tr=training_rows(s,h,"2019-07-01")
        assert (tr[f"label_end_{h}"]<pd.Timestamp("2019-07-01")).all()

def test_mapping_missing_unseen_inactive_short_history(transactions):
    cats=fit_category_map(transactions)
    assert "NEW" not in cats
    s=make_snapshot(transactions,"2019-04-01",cats).set_index("customer_id")
    assert s.loc["b","spend_30"]==0
    assert s.loc["c","history_days"]==59
    assert np.isfinite(s[feature_columns(s.reset_index())]).all().all()
    assert s.loc["a",f"category_share_{len(cats)+1:02}"]>0

@pytest.mark.parametrize("budget,cost,expected",[(0,1,0),(1000,1,3),(.3,.1,3),(2.9,1,2)])
def test_capacity(budget,cost,expected):
    assert capacity(budget,cost,3)==expected

@pytest.mark.parametrize("budget,cost",[(-1,1),(1,0),(1,-1),(np.inf,1),(1,np.nan)])
def test_invalid_budget(budget,cost):
    with pytest.raises(ValueError): capacity(budget,cost,3)

def test_save_reload_and_coherence(transactions,tmp_path):
    s=make_snapshot(transactions,"2019-01-01",["BOOK"])
    cols=feature_columns(s)
    models={h:SpendingModel(candidate_specs()[2],h,cols).fit(s) for h in [90,180]}
    bundle=ModelBundle(["BOOK"],models,"test")
    p=predict_export(bundle,s)
    joblib.dump(bundle,tmp_path/"m.joblib")
    assert_frame_equal(p,predict_export(joblib.load(tmp_path/"m.joblib"),s))
    pivot=p.pivot(index="customer_id",columns="horizon",values="predicted_spending")
    assert (pivot[180]>=pivot[90]).all()
    assert (p.predicted_spending>=0).all()

def test_export_matches_budget_selection(transactions):
    s=make_snapshot(transactions,"2019-01-01",[])
    b=ModelBundle([],{h:SpendingModel(candidate_specs()[0],h,feature_columns(s)).fit(s) for h in [90,180]},"test")
    f=predict_export(b,s).query("horizon==90")
    comparison,selected=compare_audiences(f,1,1)
    exported=pd.read_csv(io.BytesIO(export_selection(selected)))
    assert exported.customer_id.tolist()==selected.customer_id.tolist()
    assert len(exported)==1
    assert comparison.contacts.eq(1).all()
    assert compare_audiences(f,0,1)[0].actual_spending_covered.eq(0).all()

def test_repeated_horizons_rejected(transactions):
    with pytest.raises(ValueError):
        select_audience(pd.DataFrame({"customer_id":["a","a"]}))

def test_real_input_rejects_unknown_checksum(tmp_path):
    p=tmp_path/"bad.csv"
    p.write_text("bad\n1\n")
    with pytest.raises(ValueError,match="MD5 mismatch"): load_transactions(p)

def test_normalization_rejection_and_duplicates(tmp_path):
    rows=[{"Survey ResponseID":" a ","Order Date":"2018-01-01","Purchase Price Per Unit":"1.005","Quantity":"2","ASIN/ISBN (Product Code)":"","Category":"","Title":"","Shipping Address State":""}]
    rows += [rows[0].copy(),{**rows[0],"Quantity":"1.5"},{**rows[0],"Order Date":"2024-08-15"},{**rows[0],"Survey ResponseID":""},{**rows[0],"Purchase Price Per Unit":"nan"}]
    p=tmp_path/"data.csv"
    pd.DataFrame(rows).to_csv(p,index=False)
    f,a=load_transactions(p,verify_source=False)
    assert len(f)==2 and f.value_cents.tolist()==[202,202]
    assert a["identical_rows_retained"]==1
    assert a["exclusions_sequential"]["invalid_quantity"]==1
    assert a["exclusions_sequential"]["after_2022_10_31"]==1
    assert f.category.astype(str).eq("UNKNOWN").all()

def test_bootstrap_keeps_customer_clusters(monkeypatch):
    import amazon_clv.metrics as metrics_module
    original_evaluate=metrics_module.evaluate
    def assert_paired_observations(y,p):
        values=np.asarray(y)
        # a has targets 1 and 3 at its two dates, b has targets 2 and 4.
        # Every cluster draw must preserve matching multiplicities at both dates.
        assert (values==1).sum()==(values==3).sum()
        assert (values==2).sum()==(values==4).sum()
        return original_evaluate(y,p)
    monkeypatch.setattr(metrics_module,"evaluate",assert_paired_observations)
    f=pd.DataFrame({"customer_id":["a","b","a","b"],"actual_spending":[1,2,3,4],"predicted_spending":[1,2,3,4],"historical_score":[1,2,3,4]})
    result=bootstrap(f,20)
    assert all(r["customers"]==2 for r in result)
    assert next(r for r in result if r["metric"]=="rmse")["upper_95"]==0

def test_baseline_retained_without_ml_improvement():
    summary=pd.DataFrame([{"name":"trailing_90","kind":"baseline","complexity":0,"mean_rmse":100,"mean_capture_20":.4},{"name":"hgb","kind":"hgb","complexity":3,"mean_rmse":100.5,"mean_capture_20":.5}])
    assert choose_candidate(summary)=="trailing_90"
