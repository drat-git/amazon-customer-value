"""Derive all narrative facts from saved evidence. Never fit or tune models."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from amazon_clv.metrics import capture

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/"runs"/"main"
def records(df):
    return json.loads(df.to_json(orient="records",date_format="iso"))

# Add direct historical-ranking gains to the completed evidence tables.
# This changes reporting fields only, not predictions, candidates, or model selection.
for run in [RUN,RUN/"no_gift_cards"]:
    p=pd.read_csv(run/"customer_predictions.csv")
    m=pd.read_csv(run/"test_metrics.csv")
    for (h,d),f in p.groupby(["horizon","scoring_date"]):
        mask=m.horizon.eq(h)&m.scoring_date.eq(d)
        for frac in [.1,.2]:
            key=int(frac*100)
            base=capture(f.actual_spending,f.historical_score,frac)
            m.loc[mask,f"historical_capture_{key}"]=base
            m.loc[mask,f"capture_{key}_gain_pp"]=100*(m.loc[mask,f"capture_{key}"]-base)
    m.to_csv(run/"test_metrics.csv",index=False)
primary=pd.read_csv(RUN/"test_metrics.csv")
sensitivity=pd.read_csv(RUN/"no_gift_cards"/"test_metrics.csv")
gift=pd.concat([primary.loc[primary.selected].assign(analysis="Primary (gift cards retained)"),sensitivity.loc[sensitivity.selected].assign(analysis="Sensitivity (gift cards excluded)")])
gift.to_csv(RUN/"gift_sensitivity.csv",index=False)
audit=json.loads((RUN/"data_audit.json").read_text())
selection=json.loads((RUN/"frozen_selection.json").read_text())
pred=pd.read_csv(RUN/"customer_predictions.csv")
concentration=pd.read_csv(RUN/"concentration.csv")
val=pd.read_csv(RUN/"validation_metrics.csv")
valsummary=val.groupby(["horizon","name","kind"],as_index=False).agg(mean_rmse=("rmse","mean"),mean_capture_20=("capture_20","mean"))
ci=pd.read_csv(RUN/"bootstrap_intervals.csv")
market=pd.read_csv(RUN/"marketing_comparison.csv")
chosen=primary.loc[primary.selected].copy()
examples=[]
for h in [90,180]:
    f=pred.loc[pred.horizon.eq(h)&pred.scoring_date.eq("2022-01-01")].sort_values("predicted_spending")
    for label,idx in [("Low forecast",0),("Median forecast",len(f)//2),("High forecast",int(len(f)*.95))]:
        examples.append({"example":label,"horizon":h,**f.iloc[idx].to_dict()})
summary={"audit":audit,"selection":selection,"manifest":json.loads((RUN/"manifest.json").read_text()),"selected_metrics":records(chosen),"all_metrics":records(primary),"validation_summary":records(valsummary),"calibration":records(pd.read_csv(RUN/"calibration.csv")),"uncertainty":records(ci),"marketing":records(market),"sensitivity":records(gift),"segments":records(pd.read_csv(RUN/"segment_errors.csv")),"split_audit":records(pd.read_csv(RUN/"split_audit.csv")),"concentration":[{"customer_fraction":float(x),"spending_fraction":float(np.interp(x,concentration.customer_fraction,concentration.spending_fraction))} for x in np.linspace(0,1,21)],"examples":examples}
(ROOT/"reports"/"release_data.json").write_text(json.dumps(summary,indent=2)+"\n")
lines=["# Measured results","","Historical demonstration. All values below derive from the saved real-data run. Model choices froze before 2022 test evaluation.","",f"Source MD5: `{audit['md5']}` (verified). {audit['valid_rows']:,} retained rows, {audit['valid_customers']:,} accounts, ${audit['total_value_cents']/100:,.2f} recorded value. {sum(audit['exclusions_sequential'].values()):,} rows excluded, all for dates after October 31, 2022. {audit['identical_rows_retained']:,} identical rows retained. {audit['gift_rows']:,} title-matched gift rows retained in primary.","","## Frozen choices","",f"- 90 days: `{selection['selected']['90']['name']}`.",f"- 180 days: `{selection['selected']['180']['name']}`.","- Category vocabulary from 2018 only. Final training labels finish before 2022-01-01. Same fitted bundle at both test dates.","","## Untouched 2022 evaluation","","| Date | Days | Accounts | MAE | RMSE | WAPE | Normalized RMSE | Top-20% capture | Gain vs historical ranking |","|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
for _,r in chosen.iterrows():
    lines.append(f"| {r.scoring_date} | {r.horizon} | {r.n:,} | ${r.mae:,.2f} | ${r.rmse:,.2f} | {r.wape:.1%} | {r.normalized_rmse:.3f} | {r.capture_20:.1%} | {r.capture_20_gain_pp:+.2f} pp |")
lines += ["","Historical ranking uses unadjusted trailing-365-day spending. Candidate 180-day baseline predictions also receive the shared horizon-coherence constraint, so their ranking can differ from raw historical ranking.","","## Total calibration and coherence","","| Date | Days | Predicted total | Actual total | Ratio | Adjusted forecasts |","|---|---:|---:|---:|---:|---:|"]
for _,r in chosen.iterrows(): lines.append(f"| {r.scoring_date} | {r.horizon} | ${r.predicted_total:,.2f} | ${r.actual_total:,.2f} | {r.total_ratio:.3f} | {r.adjustment_rate:.2%} |")
lines += ["","## Conditional customer-bootstrap uncertainty","","500 resamples. The pooled dates repeat customers and overlap forecast windows. All rows from a sampled customer stay together. These intervals condition on fitted models and do not fix selection or temporal bias.","","| Days | Metric | Estimate | 95% interval |","|---:|---|---:|---:|"]
for _,r in ci.loc[ci.scope.eq("Both test dates")].iterrows(): lines.append(f"| {r.horizon} | {r.metric} | {r.estimate:.4f} | [{r.lower_95:.4f}, {r.upper_95:.4f}] |")
lines += ["","## Illustrative budget: $1,000 at $1/contact, January 2022","","| Days | Strategy | Contacts | Actual spending covered | Coverage | Overlap with predicted audience |","|---:|---|---:|---:|---:|---:|"]
for _,r in market.loc[market.scoring_date.eq("2022-01-01")].iterrows(): lines.append(f"| {r.horizon} | {r.strategy} | {r.contacts:,} | ${r.actual_spending_covered:,.2f} | {r.coverage_fraction:.1%} | {r.overlap_with_predicted:.1%} |")
lines += ["","Covered spending is not incremental campaign revenue. The budget and contact cost are assumptions.","","## Gift sensitivity","","| Analysis | Date | Days | Selected model | RMSE | Normalized RMSE | Capture 20% |","|---|---|---:|---|---:|---:|---:|"]
for _,r in gift.iterrows(): lines.append(f"| {r.analysis} | {r.scoring_date} | {r.horizon} | {r.model} | ${r.rmse:,.2f} | {r.normalized_rmse:.3f} | {r.capture_20:.1%} |")
lines += ["","The sensitivity independently repeats selection/refitting without matching titles, changing targets and potentially cohorts. It is not a causal contrast.","","## Error groups","","Groups can overlap. Low-history groups are small and their metrics are unstable. Historical high spending is defined from features, not future outcomes.","","| Date | Days | Group | Accounts | RMSE | WAPE |","|---|---:|---|---:|---:|---:|"]
for r in summary["segments"]:
    lines.append(f"| {r['scoring_date']} | {r['horizon']} | {r['segment']} | {r['n']:,} | ${r['rmse']:,.2f} | {r['wape']:.1%} |")
lines += ["","## Examples for an interview","","Examples are selected by forecast percentile, not by observed outcome. They are descriptive, not success-case cherry-picks.","","| Example | Days | Account | Predicted | Actual | Recency | History |","|---|---:|---|---:|---:|---:|---:|"]
for r in examples: lines.append(f"| {r['example']} | {r['horizon']} | {r['customer_id']} | ${r['predicted_spending']:,.2f} | ${r['actual_spending']:,.2f} | {r['recency_days']:.0f} | {r['history_days']:.0f} |")
lines += ["","## Interview interpretation","","State both error and ranking results, then acknowledge that ranking gain may be small or negative even when RMSE improves. Discuss normalized errors instead of choosing a horizon by its dollar RMSE. Inspect calibration and conditional uncertainty before recommending a horizon. Do not tune models using these final test outcomes."]
(ROOT/"docs"/"RESULTS.md").write_text("\n".join(lines)+"\n")
print(chosen[["horizon","scoring_date","model","rmse","wape","capture_20","capture_20_gain_pp","adjustment_rate"]].to_string(index=False))
print("Release evidence and measured-results guide saved")
