# Public historical demo bundle

These are saved real-data results from the verified analysis, not synthetic
examples or live customer predictions. Source: Open e-commerce 1.0, Harvard
Dataverse version 1.0, [CC0 1.0](https://doi.org/10.7910/DVN/YGLYDY).

The bundle contains all 19,990 account/date/horizon forecasts, evaluation
tables, the concentration chart, and 776,421 account/day spending totals.
Forecast amounts and metrics are unchanged. Ordered display aliases replace
original survey identifiers and preserve audience tie-breaking. The alias
mapping is not exported. These aliases do not constitute a guarantee of
anonymity: the underlying research dataset is publicly available.

Item titles, product identifiers, shipping states, and individual purchase
rows are not included. Daily history is filtered to dates before the selected
scoring date in the customer explorer. Saved outputs keep hosting lightweight;
the dashboard does not retrain or deserialize models.

Regenerate from a completed local analysis with:

```bash
python scripts/prepare_demo.py
```

The complete analytical pipeline, model scoring, and original-data download
instructions are documented in the root README.
