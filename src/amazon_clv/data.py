"""Read-only ingestion, exact cents, provenance checks, and explicit exclusions."""
from __future__ import annotations
import hashlib
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import numpy as np
import pandas as pd

START = pd.Timestamp("2018-01-01")
OBSERVATION_END = pd.Timestamp("2022-11-01")  # exclusive
EXPECTED_MD5 = "3549d72735b1211ab009ff0177b94bd9"
GIFT_RULE = r"gift\s+card|gift\s+code|digital\s+code|amazon\s+reload"
COLUMNS = {
    "Survey ResponseID": "customer_id", "Order Date": "date",
    "Purchase Price Per Unit": "price", "Quantity": "quantity",
    "ASIN/ISBN (Product Code)": "product_id", "Category": "category",
    "Title": "title", "Shipping Address State": "state",
}

def file_hash(path: str | Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def _cents(value: str) -> int | None:
    try:
        x = Decimal(str(value))
        if not x.is_finite() or x <= 0 or x > Decimal("100000000"):
            return None
        cents = int((x * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return cents if cents > 0 else None
    except (InvalidOperation, ValueError, OverflowError):
        return None

def load_transactions(path: str | Path, *, verify_source: bool = True,
                      observation_end: pd.Timestamp = OBSERVATION_END) -> tuple[pd.DataFrame, dict]:
    """Read a source CSV without modifying it. Exclusion counts are sequential."""
    md5 = file_hash(path, "md5")
    if verify_source and md5 != EXPECTED_MD5:
        raise ValueError(f"Source MD5 mismatch: {md5}. Use --allow-unverified only for deliberate alternate inputs.")
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = set(COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f"Missing required source columns: {sorted(missing)}")
    df = raw.rename(columns=COLUMNS)[list(COLUMNS.values())].copy()
    audit = {"source_name": Path(path).name, "bytes": Path(path).stat().st_size,
             "md5": md5, "sha256": file_hash(path, "sha256"),
             "checksum_verified": md5 == EXPECTED_MD5,
             "source_rows": len(df), "source_schema": raw.columns.tolist(),
             "dataset_doi": "10.7910/DVN/YGLYDY", "license": "CC0-1.0",
             "observation_start": str(START.date()), "observation_end_exclusive": str(observation_end.date())}
    for c in ["customer_id", "product_id", "category", "title", "state"]:
        df[c] = df[c].str.strip()
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
    audit["source_date_min"] = str(df.date.min().date())
    audit["source_date_max"] = str(df.date.max().date())
    audit["source_customers"] = int(df.customer_id.nunique())
    audit["source_rows_by_year"] = {str(k): int(v) for k,v in df.date.dt.year.value_counts().sort_index().items()}
    prices = {v: _cents(v) for v in df.price.unique()}
    df["unit_price_cents"] = df.price.map(prices)
    df["quantity"] = pd.to_numeric(df.quantity, errors="coerce")
    checks = [
        ("missing_customer_id", df.customer_id.eq("")),
        ("invalid_date", df.date.isna()),
        ("invalid_price", df.unit_price_cents.isna()),
        ("invalid_quantity", ~np.isfinite(df.quantity) | (df.quantity <= 0) | (df.quantity % 1 != 0) | (df.quantity > 1_000_000)),
        ("before_2018", df.date < START),
        ("after_2022_10_31", df.date >= observation_end),
    ]
    remaining = pd.Series(True, index=df.index)
    excluded = {}
    for name, invalid in checks:
        excluded[name] = int((remaining & invalid).sum())
        remaining &= ~invalid
    audit["exclusions_sequential"] = excluded
    late = df.loc[df.date >= observation_end]
    audit["later_records_by_year"] = {str(k): int(v) for k,v in late.date.dt.year.value_counts().sort_index().items()}
    df = df.loc[remaining].copy()
    df["quantity"] = df.quantity.astype("int64")
    df["unit_price_cents"] = df.unit_price_cents.astype("int64")
    df["value_cents"] = df.unit_price_cents * df.quantity
    for c in ["category", "product_id", "title", "state"]:
        audit[f"missing_{c}"] = int(df[c].eq("").sum())
        df[c] = df[c].replace("", "UNKNOWN")
    df["category"] = df.category.str.upper()
    df["product_id"] = df.product_id.str.upper()
    df["state"] = df.state.str.upper()
    df["is_gift"] = df.title.str.contains(GIFT_RULE, case=False, regex=True, na=False)
    audit["gift_rule"] = GIFT_RULE
    audit["gift_rows"] = int(df.is_gift.sum())
    audit["gift_value_cents"] = int(df.loc[df.is_gift, "value_cents"].sum())
    audit["identical_rows_retained"] = int(df.duplicated(subset=["customer_id", "date", "unit_price_cents", "quantity", "product_id", "title", "category", "state"]).sum())
    audit["valid_rows"] = len(df)
    audit["valid_customers"] = int(df.customer_id.nunique())
    audit["total_value_cents"] = int(df.value_cents.sum())
    df = df.drop(columns="price").sort_values(["date", "customer_id"], kind="stable").reset_index(drop=True)
    for c in ["customer_id", "category", "product_id", "state"]:
        df[c] = df[c].astype("category")
    return df, audit
