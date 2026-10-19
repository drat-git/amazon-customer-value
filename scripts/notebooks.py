"""Create and execute four explanatory notebooks, each from a clean kernel."""
import os
from pathlib import Path
import nbformat as nbf
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]
setup='''from pathlib import Path
import json
import numpy as np
import pandas as pd
from IPython.display import display, Image, Markdown
ROOT = Path.cwd()
if ROOT.name == "notebooks":
    ROOT = ROOT.parent
RUN = Path(__import__("os").environ.get("AMAZON_CLV_RUN", str(ROOT / "runs" / "main")))
assert (RUN / "manifest.json").exists(), "Run python -m amazon_clv run first"
audit = json.loads((RUN / "data_audit.json").read_text())
manifest = json.loads((RUN / "manifest.json").read_text())
pd.set_option("display.max_columns", 20)
print("Source MD5:", audit["md5"], "| Model version:", manifest["run_version"])
'''

def md(text): return nbf.v4.new_markdown_cell(text)
def code(text): return nbf.v4.new_code_cell(text)

notebooks={
"01_data_quality.ipynb":[
md("# 01 · Data quality and provenance\n\nHistorical demonstration. Audit real, consented item histories without modifying the original. Primary analysis retains gift cards. [Dataset](https://doi.org/10.7910/DVN/YGLYDY), [paper](https://www.nature.com/articles/s41597-024-03329-6)."),code(setup),
md("## Check identity and reconcile exclusions\nMD5 verifies the mirror's bytes against the original deposit. SHA256 tracks this exact analytical input. Neither certifies each source record's correctness."),
code('''assert audit["checksum_verified"]
assert audit["valid_rows"] + sum(audit["exclusions_sequential"].values()) == audit["source_rows"]
display(pd.Series({k:audit[k] for k in ["source_rows","source_customers","valid_rows","valid_customers","source_date_min","source_date_max","identical_rows_retained","gift_rows"]},name="Audit"))
display(pd.Series(audit["exclusions_sequential"],name="Sequential excluded rows"))
display(pd.Series(audit["later_records_by_year"],name="Later dates excluded"))'''),
md("## Missing descriptions, exact purchase values, and coverage\nUNKNOWN is explicit. Identical rows remain because no order identifier resolves whether they are duplicates. Coverage ends exclusively on 2022-11-01, independently of each customer's last observed purchase."),
code('''tx = pd.read_parquet(RUN / "transactions.parquet")
assert tx.date.ge("2018-01-01").all() and tx.date.lt("2022-11-01").all()
assert (tx.value_cents == tx.unit_price_cents * tx.quantity).all()
assert tx.value_cents.sum() == audit["total_value_cents"]
display(pd.Series({k:v for k,v in audit.items() if k.startswith("missing_")},name="Explicit missing descriptions"))
print(f"Recorded purchase value: ${tx.value_cents.sum()/100:,.2f}")
display(tx.groupby(tx.date.dt.year).agg(item_rows=("value_cents","size"),accounts=("customer_id","nunique"),value_cents=("value_cents","sum")))'''),
code('''display(Image(filename=str(RUN / "charts" / "monthly_spending.png")))
display(Image(filename=str(RUN / "charts" / "concentration.png")))'''),
md("## Interpretation\nThis is a consent-selected retrospective account cohort, with roughly 5,000 accounts rather than 1.85 million independent customers. Shared accounts, selection at recruitment, left-truncated history, and source anomalies limit inference. Customer purchase value differs from Amazon net revenue/profit. Do not use 2023/2024 records to claim a more recent validated cohort.")],
"02_feature_engineering.ipynb":[
md("# 02 · Snapshot features and targets\n\nOne account at a scoring date is the unit of prediction. Feature history is strictly earlier. Targets are half-open 90/180-day windows. Frequency means purchase days."),code(setup),
code('''from amazon_clv.features import make_snapshot, feature_columns, training_rows
mapping = json.loads((RUN / "category_mapping.json").read_text())
categories = mapping["categories"][:-2]
snapshots = pd.read_parquet(RUN / "snapshots.parquet")
display(pd.DataFrame({"feature":mapping["feature_names"],"category":mapping["categories"]}))
print("Numeric feature count:",len(feature_columns(snapshots)))
display(snapshots.groupby("scoring_date").agg(accounts=("customer_id","size"),available_90=("target_90","count"),available_180=("target_180","count"),zeros_90=("target_90",lambda s:s.eq(0).sum())).tail(12))'''),
md("## Demonstrate future invariance\nAppend a future high-value transaction and recompute the earlier snapshot. Every predictive feature must remain exactly unchanged. Targets may change when future observations change, as they should."),
code('''tx = pd.read_parquet(RUN / "transactions.parquet")
ids = snapshots.loc[snapshots.scoring_date.eq("2022-01-01"),"customer_id"].head(12)
small = tx.loc[tx.customer_id.astype(str).isin(ids)].copy()
before = make_snapshot(small,"2022-01-01",categories)
extra = small.iloc[[0]].copy()
extra["date"] = pd.Timestamp("2022-02-01")
extra["value_cents"] = 99999999
after = make_snapshot(pd.concat([small,extra],ignore_index=True),"2022-01-01",categories)
pd.testing.assert_frame_equal(before[["customer_id"]+feature_columns(before)],after[["customer_id"]+feature_columns(after)])
print("PASS: adding future purchases cannot change earlier features")
display(before[["customer_id","recency_days","history_days","spend_90","purchase_days_90","target_90","target_180"]].head())'''),
md("## Enforce label availability\nHistorical features alone are insufficient. A training target must also finish before the scoring cutoff. The final fit can include mature 2021 examples after validation choices freeze."),
code('''split = pd.read_csv(RUN / "split_audit.csv")
assert (pd.to_datetime(split.max_label_end) < pd.to_datetime(split.cutoff)).all()
display(split)
for h in [90,180]:
    train = training_rows(snapshots,h,"2022-01-01")
    assert train.scoring_date.lt("2022-01-01").all()
    assert train[f"target_{h}"].notna().all()
    print(f"{h}d final training rows: {len(train):,}")'''),
md("## Design tradeoffs\nFreeze top categories from 2018 to eliminate future category popularity from the representation. UNKNOWN handles missing data and OTHER handles new categories. History length measures observed tenure, not true account age. Month sine/cosine features encode cyclic seasonality. Identifiers and late survey responses never enter features. Read DATA_DICTIONARY.md for every formula.")],
"03_modeling.ipynb":[
md("# 03 · Chronological modeling and honest evaluation\n\nTen bounded candidates per horizon. Select on January/July 2021, then freeze and evaluate January/May 2022. This notebook reads the completed models instead of silently retraining."),code(setup),
code('''validation = pd.read_csv(RUN / "validation_metrics.csv")
summary = validation.groupby(["horizon","name"]).agg(mean_rmse=("rmse","mean"),mean_capture_20=("capture_20","mean"))
display(summary)
selection = json.loads((RUN / "frozen_selection.json").read_text())
display(selection)
metrics = pd.read_csv(RUN / "test_metrics.csv")
display(metrics.loc[metrics.selected,["horizon","scoring_date","model","mae","rmse","wape","normalized_rmse","predicted_total","actual_total","capture_10","capture_20","adjustment_rate"]])'''),
md("## Same serialized model, same predictions\nBoth historical dates use the same fitted bundle. Coherent 180-day forecasts are max(raw180,90-day forecast). This adjustment was already included in validation."),
code('''import joblib
from amazon_clv.pipeline import predict_export
bundle = joblib.load(RUN / "bundle" / "models.joblib")
snapshots = pd.read_parquet(RUN / "snapshots.parquet")
test = snapshots.loc[snapshots.scoring_date.isin(pd.to_datetime(["2022-01-01","2022-05-01"]))]
from threadpoolctl import threadpool_limits
with threadpool_limits(limits=4):
    reloaded = predict_export(bundle,test)
saved = pd.read_parquet(RUN / "customer_predictions.parquet")
np.testing.assert_allclose(reloaded.predicted_spending,saved.predicted_spending,rtol=0,atol=1e-8)
pivot = saved.pivot(index=["customer_id","scoring_date"],columns="horizon",values="predicted_spending")
assert pivot[180].ge(pivot[90]).all()
print("PASS: saved bundle reproduces every test prediction and horizon coherence")'''),
code('''display(Image(filename=str(RUN / "charts" / "model_errors.png")))
display(Image(filename=str(RUN / "charts" / "calibration.png")))
display(Image(filename=str(RUN / "charts" / "horizon_comparison.png")))'''),
md("## Uncertainty and robustness\n500 account-level bootstrap resamples keep repeated account observations together. Intervals are conditional on the fitted models, with temporal/sample-selection uncertainty unresolved. Overlapping test windows are dependent. Smaller 90-day dollar error alone cannot establish a better business horizon."),
code('''ci = pd.read_csv(RUN / "bootstrap_intervals.csv")
display(ci.loc[ci.scope.eq("Both test dates")])
display(pd.read_csv(RUN / "segment_errors.csv"))
display(pd.read_csv(RUN / "gift_sensitivity.csv")[["analysis","scoring_date","horizon","model","rmse","normalized_rmse","capture_20"]])
display(Image(filename=str(RUN / "charts" / "gift_sensitivity.png")))
display(pd.read_csv(RUN / "predictive_associations.csv").sort_values("rmse_increase",ascending=False).head(15))'''),
md("## Interpretation\nFeature importance measures predictive association, not interventions. The gift sensitivity changes the target and can change cohort membership and selected model. Report measured outcomes even if a baseline or alternative horizon is stronger on a particular metric. No test-outcome tuning follows this notebook.")],
"04_marketing_analysis.ipynb":[
md("# 04 · Customer-value coverage under a contact budget\n\nHistorical demonstration on January 1, 2022. Budget and unit cost are illustrative. Covered purchase value does not measure incremental campaign revenue."),code(setup),
code('''from amazon_clv.marketing import capacity,compare_audiences,export_selection
pred = pd.read_parquet(RUN / "customer_predictions.parquet")
frame = pred.loc[pred.scoring_date.eq("2022-01-01") & pred.horizon.eq(90)].copy()
comparison,selection = compare_audiences(frame,budget=1000,contact_cost=1)
display(comparison)
display(selection.head(10))
print("Selected",len(selection),"accounts out of",len(frame))'''),
md("## Check budget edge cases and exported identity\nAll strategies get equal capacity. A seeded random benchmark makes this demo reproducible. The exact displayed selection feeds the CSV download."),
code('''import io
exported = pd.read_csv(io.BytesIO(export_selection(selection)))
assert exported.customer_id.tolist() == selection.customer_id.tolist()
assert capacity(0,1,len(frame)) == 0
assert capacity(10**9,1,len(frame)) == len(frame)
assert capacity(.3,.1,len(frame)) == 3
assert compare_audiences(frame,0,1)[0].actual_spending_covered.eq(0).all()
for cost in [0,-1,float("inf")]:
    try:
        capacity(100,cost,len(frame))
        raise AssertionError("Invalid cost should fail")
    except ValueError:
        pass
print("PASS: zero/oversized budgets, cost validation, cent arithmetic, exact export")'''),
code('''display(Image(filename=str(RUN / "charts" / "marketing_coverage.png")))
display(Image(filename=str(RUN / "charts" / "ranking_capture.png")))
rows=[]
for budget in [0,100,500,1000,2500,10000]:
    c,_=compare_audiences(frame,budget,1)
    rows.append(c.assign(budget=budget))
display(pd.concat(rows,ignore_index=True))'''),
md("## What a marketer can claim\nAt this historical date, the selection covers a measured fraction of future recorded spending within an assumed uniform contact budget. Audience overlap shows how much selection changes relative to existing heuristics. It does not show how spending would change after contact. Randomized treatments, observed response, offer/contact costs, and contribution margins are required for causal marketing ROI or profit optimization. Shared accounts and the retrospective cohort limit extrapolation. Read INTERVIEW_GUIDE.md for a full technical explanation.")]
}

for name,cells in notebooks.items():
    path=ROOT/"notebooks"/name
    nb=nbf.v4.new_notebook(cells=cells,metadata={"kernelspec":{"name":"python3","display_name":"Python 3.12 (amazon-clv)","language":"python"},"language_info":{"name":"python","version":"3.12"}})
    nbf.write(nb,path)
    print("Executing clean kernel:",name,flush=True)
    NotebookClient(nb,timeout=600,kernel_name="python3",resources={"metadata":{"path":str(ROOT)}}).execute()
    nbf.write(nb,path)
    assert all(c.get("execution_count") is not None for c in nb.cells if c.cell_type=="code")
    assert not any(o.output_type=="error" for c in nb.cells if c.cell_type=="code" for o in c.outputs)
print("Four notebooks executed without errors")
