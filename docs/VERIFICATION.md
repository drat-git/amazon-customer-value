# Verification record

Real-data local release, October 18, 2026. No test-outcome model tuning.

## Automated and analytical checks

- 23 automated checks passed in the original environment and in a second fresh Python 3.12 environment.
- Complete explicitly synthetic end-to-end smoke passed before real-data execution.
- Both original and fresh environments installed the pinned dependency closure without dependency conflicts.
- Every final-test target is observed, forecasts nonnegative, and horizons coherent.
- Every validation/final training label ends strictly before its cutoff.
- Metrics, selected audience IDs, and report/slide evidence reconcile to prediction rows.
- Batch CLI predictions reproduce all 9,982 January account-horizon records.
- Four notebooks contain executed code cells with zero error outputs.
- Final PDF has 10 pages and final editable PPTX has 12 slides.
- Fresh environment full rerun reproduces primary and gift-sensitivity choices, every prediction, and all bootstrap intervals.

## Notebook and visual review

Four notebooks executed from separate clean Python kernels, with all code cells executed and no cell errors. They were refreshed after final chart formatting fixes.

All 10 PDF pages were rendered and visually inspected. Refreshed pages 2, 8, and 9 were rechecked after edits. All 12 presentation slides were rendered and inspected. Finalized PPTX previews are pixel-identical to the reviewed authoring previews for all 12 slides. The finalizer verified package integrity, geometry, fonts, native chart/workbook references, five native tables, nine native charts, and successful Artifact Tool import, with no findings or warnings. Native PowerPoint application testing was unavailable and is not claimed.

## Running dashboard and downloads

Launched the local Streamlit dashboard on 127.0.0.1:8501 with usage telemetry disabled. Browser inspection confirmed historical labels, January 2022 default, horizon/model display, budget controls, ranked audience table, coverage chart, and zero-budget capacity/cost/value of zero. The custom browser download contained exactly the same 1,000 customer IDs in the same order as the displayed selection. Automated dashboard testing visited every view and changed date/horizon and oversized budget. Batch scoring reproduced all 9,982 January account-horizon forecasts within 1e-8 dollars.

## Reproducibility

A second isolated environment installed requirements.lock.txt from scratch and executed the complete original-data pipeline, including the independent gift sensitivity and all 500-resample uncertainty calculations. Every selected model, every primary/sensitivity prediction, and all bootstrap interval values reproduced within the declared numerical tolerances.

## Artifact hashes

| Artifact | SHA256 |
|---|---|
| amazon_customer_value_report.pdf | `bba29dbe0e697f7f25591f8d3abe4a603597500ad5d309f03ea2441649fcd16a` |
| amazon_customer_value_presentation.pptx | `d38e5145ed25b2991b778ac12926af8e3aeafacaa429fa8ff97dad8cf6c62cf8` |

Detailed command output and checkpoints remain under the ignored runs/ directory. Activity, failures, fixes, and decision rationales appear in WORK_LOG.md. These checks establish this release's historical reproducibility, not future prospective performance or causal marketing validity.
