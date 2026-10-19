"""Export a portable dashboard bundle from a completed, verified local run.

Preserves predictions and metrics; replaces original account IDs with ordered
display aliases and aggregates purchase history to account/day totals.
"""
from pathlib import Path
import argparse
import json
import shutil
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def prepare_demo(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    predictions = pd.read_parquet(source / "customer_predictions.parquet")
    transactions = pd.read_parquet(source / "transactions.parquet")
    ids = sorted(transactions.customer_id.astype(str).unique())
    aliases = {customer: f"Account-{index:05d}" for index, customer in enumerate(ids, 1)}
    # Ordered aliases preserve the original stable tie-breaking in audience ranks.
    predictions["customer_id"] = predictions.customer_id.astype(str).map(aliases)
    if predictions.customer_id.isna().any():
        raise ValueError("Every prediction must match a purchase-history account")
    predictions.to_parquet(destination / "customer_predictions.parquet", index=False)
    daily = transactions.groupby(["customer_id", "date"], as_index=False).agg(
        quantity=("quantity", "sum"), value_cents=("value_cents", "sum")
    )
    daily["customer_id"] = daily.customer_id.astype(str).map(aliases)
    daily.to_parquet(destination / "daily_history.parquet", index=False)
    for name in ["manifest.json", "data_audit.json", "bundle/manifest.json",
                 "test_metrics.csv", "calibration.csv", "bootstrap_intervals.csv",
                 "segment_errors.csv", "gift_sensitivity.csv", "charts/concentration.png"]:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, target)
    manifest_path = destination / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["public_demo"] = {
        "account_ids": "Ordered display aliases; no original survey IDs",
        "history": "Daily quantity and spending totals; item details omitted",
        "forecasts": "Unmodified saved forecasts from the verified historical run",
        "training": "No training or model deserialization at app startup",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Prepared {len(predictions):,} predictions and {len(daily):,} account-days in {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "runs/main")
    parser.add_argument("--output", type=Path, default=ROOT / "demo")
    args = parser.parse_args()
    prepare_demo(args.source, args.output)
