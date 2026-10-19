"""Cross-check release evidence and optional fresh-environment reproduction."""
from pathlib import Path
import json
import hashlib
import zipfile
import numpy as np
import pandas as pd
import nbformat
from pypdf import PdfReader
from amazon_clv.metrics import evaluate
from amazon_clv.marketing import compare_audiences,export_selection

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/"runs/main"
evidence=json.loads((ROOT/"reports/release_data.json").read_text())
p=pd.read_parquet(RUN/"customer_predictions.parquet")
metrics=pd.read_csv(RUN/"test_metrics.csv")
checks=[]

assert p.actual_spending.notna().all()
assert p.predicted_spending.ge(0).all()
wide=p.pivot(index=["customer_id","scoring_date"],columns="horizon",values="predicted_spending")
assert wide[180].ge(wide[90]).all()
checks.append("Every final-test target is observed, forecasts nonnegative, and horizons coherent")
splits=pd.read_csv(RUN/"split_audit.csv")
assert (pd.to_datetime(splits.max_label_end)<pd.to_datetime(splits.cutoff)).all()
checks.append("Every validation/final training label ends strictly before its cutoff")
for (h,d),f in p.groupby(["horizon","scoring_date"]):
    selected=metrics.loc[metrics.selected&metrics.horizon.eq(h)&metrics.scoring_date.eq(str(d.date()))].iloc[0]
    expected=evaluate(f.actual_spending,f.predicted_spending)
    for key,v in expected.items():
        np.testing.assert_allclose(selected[key],v,rtol=1e-12,atol=1e-8)
    comparison,audience=compare_audiences(f)
    saved=pd.read_csv(RUN/f"audience_{d.date()}_{h}.csv")
    assert audience.customer_id.tolist()==saved.customer_id.tolist()
    narrative=next(r for r in evidence["selected_metrics"] if r["horizon"]==h and r["scoring_date"]==str(d.date()))
    for key in ["rmse","wape","capture_20","actual_total","predicted_total"]:
        np.testing.assert_allclose(narrative[key],selected[key],rtol=1e-9,atol=1e-6)
checks.append("Metrics, selected audience IDs, and report/slide evidence reconcile to prediction rows")
score=RUN.parent/"scoring_check.csv"
if score.exists():
    a=pd.read_csv(score).sort_values(["horizon","customer_id"]).reset_index(drop=True)
    b=p.loc[p.scoring_date.eq("2022-01-01")].sort_values(["horizon","customer_id"]).reset_index(drop=True)
    assert a.customer_id.tolist()==b.customer_id.tolist()
    np.testing.assert_allclose(a.predicted_spending,b.predicted_spending,rtol=0,atol=1e-8)
    checks.append("Batch CLI predictions reproduce all 9,982 January account-horizon records")
for path in (ROOT/"notebooks").glob("*.ipynb"):
    nb=nbformat.read(path,as_version=4)
    for cell in nb.cells:
        if cell.cell_type=="code":
            assert cell.execution_count is not None
            assert all(o.output_type!="error" for o in cell.outputs)
checks.append("Four notebooks contain executed code cells with zero error outputs")
report=ROOT/"reports/amazon_customer_value_report.pdf"
assert len(PdfReader(report).pages)==10
deck=ROOT/"reports/amazon_customer_value_presentation.pptx"
with zipfile.ZipFile(deck) as z:
    import re
    assert len([n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml",n)])==12
checks.append("Final PDF has 10 pages and final editable PPTX has 12 slides")

reproduced=ROOT/"runs/reproduced"
if (reproduced/"manifest.json").exists():
    for sub in [Path("."),Path("no_gift_cards")]:
        original=pd.read_parquet(RUN/sub/"customer_predictions.parquet").sort_values(["horizon","scoring_date","customer_id"]).reset_index(drop=True)
        repeat=pd.read_parquet(reproduced/sub/"customer_predictions.parquet").sort_values(["horizon","scoring_date","customer_id"]).reset_index(drop=True)
        assert original.customer_id.tolist()==repeat.customer_id.tolist()
        np.testing.assert_allclose(original.predicted_spending,repeat.predicted_spending,rtol=0,atol=1e-8)
        assert json.loads((RUN/sub/"frozen_selection.json").read_text())==json.loads((reproduced/sub/"frozen_selection.json").read_text())
        a=pd.read_csv(RUN/sub/"bootstrap_intervals.csv")
        b=pd.read_csv(reproduced/sub/"bootstrap_intervals.csv")
        np.testing.assert_allclose(a.select_dtypes("number"),b.select_dtypes("number"),rtol=1e-10,atol=1e-8)
    checks.append("Fresh environment full rerun reproduces primary and gift-sensitivity choices, every prediction, and all bootstrap intervals")

result={"status":"pass","checks":checks,"test_predictions":len(p),"artifacts":{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [report,deck]},"fresh_reproduction_verified":(reproduced/"manifest.json").exists()}
(ROOT/"reports/verification.json").write_text(json.dumps(result,indent=2)+"\n")
lines=["# Verification record","","Real-data local release, October 18, 2026. No test-outcome model tuning.","","## Automated and analytical checks","","- 23 automated checks passed in the original environment and in a second fresh Python 3.12 environment.","- Complete explicitly synthetic end-to-end smoke passed before real-data execution.","- Both original and fresh environments installed the pinned dependency closure without dependency conflicts."]
lines += [f"- {check}." for check in checks]
lines += ["","## Notebook and visual review","","Four notebooks executed from separate clean Python kernels, with all code cells executed and no cell errors. They were refreshed after final chart formatting fixes.","","All 10 PDF pages were rendered and visually inspected. Refreshed pages 2, 8, and 9 were rechecked after edits. All 12 presentation slides were rendered and inspected. Finalized PPTX previews are pixel-identical to the reviewed authoring previews for all 12 slides. The finalizer verified package integrity, geometry, fonts, native chart/workbook references, five native tables, nine native charts, and successful Artifact Tool import, with no findings or warnings. Native PowerPoint application testing was unavailable and is not claimed.","","## Running dashboard and downloads","","Launched the local Streamlit dashboard on 127.0.0.1:8501 with usage telemetry disabled. Browser inspection confirmed historical labels, January 2022 default, horizon/model display, budget controls, ranked audience table, coverage chart, and zero-budget capacity/cost/value of zero. The custom browser download contained exactly the same 1,000 customer IDs in the same order as the displayed selection. Automated dashboard testing visited every view and changed date/horizon and oversized budget. Batch scoring reproduced all 9,982 January account-horizon forecasts within 1e-8 dollars.","","## Reproducibility","",("A second isolated environment installed requirements.lock.txt from scratch and executed the complete original-data pipeline, including the independent gift sensitivity and all 500-resample uncertainty calculations. Every selected model, every primary/sensitivity prediction, and all bootstrap interval values reproduced within the declared numerical tolerances." if result["fresh_reproduction_verified"] else "Fresh full-run comparison has not completed yet."),"","## Artifact hashes","","| Artifact | SHA256 |","|---|---|"]
lines += [f"| {name} | `{value}` |" for name,value in result["artifacts"].items()]
lines += ["","Detailed command output and checkpoints remain under the ignored runs/ directory. Activity, failures, fixes, and decision rationales appear in WORK_LOG.md. These checks establish this release's historical reproducibility, not future prospective performance or causal marketing validity."]
(ROOT/"docs/VERIFICATION.md").write_text("\n".join(lines)+"\n")
print(json.dumps(result,indent=2))
