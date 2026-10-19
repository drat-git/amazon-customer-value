"""One feature implementation for model development and batch scoring."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .data import OBSERVATION_END

def fit_category_map(transactions: pd.DataFrame, cutoff="2019-01-01", top_n=12) -> list[str]:
    """Fit the frozen category vocabulary exclusively on initial training history."""
    history = transactions.loc[transactions.date < pd.Timestamp(cutoff)]
    totals = history.groupby("category", observed=True).value_cents.sum().sort_values(ascending=False)
    return [str(x) for x in totals.index if x != "UNKNOWN"][:top_n]

def make_snapshot(transactions: pd.DataFrame, as_of, categories: list[str],
                  observation_end=OBSERVATION_END, include_targets=True) -> pd.DataFrame:
    """Features use dates < as_of. Targets use [as_of, as_of + days)."""
    as_of = pd.Timestamp(as_of)
    hist = transactions.loc[transactions.date < as_of]
    grouped = hist.groupby("customer_id", observed=True)
    x = grouped.date.agg(first_date="min", last_date="max")
    x.index = x.index.astype(str)
    x["history_days"] = (as_of - x.first_date).dt.days
    x["recency_days"] = (as_of - x.last_date).dt.days
    x["lifetime_spend"] = grouped.value_cents.sum().set_axis(grouped.size().index.astype(str)) / 100
    x["lifetime_purchase_days"] = grouped.date.nunique().set_axis(grouped.size().index.astype(str))
    for days in [30, 90, 180, 365]:
        window = hist.loc[hist.date >= as_of - pd.Timedelta(days=days)]
        g = window.groupby("customer_id", observed=True)
        aggregates = g.agg(**{
            f"spend_{days}": ("value_cents", "sum"),
            f"purchase_days_{days}": ("date", "nunique"),
            f"quantity_{days}": ("quantity", "sum"),
            f"products_{days}": ("product_id", "nunique"),
            f"categories_{days}": ("category", "nunique"),
        })
        aggregates.index = aggregates.index.astype(str)
        aggregates[f"spend_{days}"] /= 100
        x = x.join(aggregates)
        x[f"spend_per_purchase_day_{days}"] = x[f"spend_{days}"] / x[f"purchase_days_{days}"].replace(0, np.nan)
        x[f"observed_days_{days}"] = np.minimum(x.history_days, days)
    win = hist.loc[hist.date >= as_of - pd.Timedelta(days=365)].copy()
    win["mapped_category"] = win.category.astype(str).where(win.category.astype(str).isin(categories + ["UNKNOWN"]), "OTHER")
    shares = win.groupby(["customer_id", "mapped_category"], observed=True).value_cents.sum().unstack(fill_value=0)
    shares.index = shares.index.astype(str)
    shares = shares.reindex(columns=categories + ["UNKNOWN", "OTHER"], fill_value=0)
    shares = shares.div(shares.sum(axis=1).replace(0, np.nan), axis=0)
    shares.columns = [f"category_share_{i:02}" for i in range(len(shares.columns))]
    x = x.join(shares)
    x["spend_trend_30"] = x.spend_30 - (x.spend_90 - x.spend_30) / 2
    x["spend_trend_90"] = x.spend_90 - (x.spend_180 - x.spend_90)
    x["spend_trend_180"] = x.spend_180 / 180 - (x.spend_365 - x.spend_180) / 185
    x["month_sin"] = np.sin(2 * np.pi * as_of.month / 12)
    x["month_cos"] = np.cos(2 * np.pi * as_of.month / 12)
    x = x.drop(columns=["first_date", "last_date"]).fillna(0)
    x["scoring_date"] = as_of
    if include_targets:
        for horizon in [90, 180]:
            end = as_of + pd.Timedelta(days=horizon)
            x[f"label_end_{horizon}"] = end
            if end <= pd.Timestamp(observation_end):
                future = transactions.loc[(transactions.date >= as_of) & (transactions.date < end)]
                target = future.groupby("customer_id", observed=True).value_cents.sum()
                target.index = target.index.astype(str)
                x[f"target_{horizon}"] = target.reindex(x.index, fill_value=0) / 100
            else:
                x[f"target_{horizon}"] = np.nan
    return x.rename_axis("customer_id").reset_index()

def feature_columns(snapshots: pd.DataFrame) -> list[str]:
    return [c for c in snapshots.columns if c not in ["customer_id", "scoring_date"] and not c.startswith(("target_", "label_end_"))]

def training_rows(snapshots: pd.DataFrame, horizon: int, cutoff, development_only=False) -> pd.DataFrame:
    """Strict conservative purge: label_end < cutoff; never randomly split snapshots."""
    mask = (snapshots[f"label_end_{horizon}"] < pd.Timestamp(cutoff)) & snapshots[f"target_{horizon}"].notna()
    if development_only:
        mask &= snapshots.scoring_date < pd.Timestamp("2021-01-01")
    return snapshots.loc[mask].copy()
