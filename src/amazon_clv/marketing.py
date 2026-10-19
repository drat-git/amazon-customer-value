"""Deterministic audience selection and contact-budget arithmetic."""
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
import numpy as np
import pandas as pd

def capacity(budget, contact_cost, eligible):
    try:
        budget, cost = Decimal(str(budget)), Decimal(str(contact_cost))
        if not budget.is_finite() or not cost.is_finite() or budget < 0 or cost <= 0:
            raise ValueError("Budget must be finite and nonnegative; contact cost must be finite and positive.")
        return min(eligible, int((budget / cost).to_integral_value(rounding=ROUND_FLOOR)))
    except InvalidOperation as e:
        raise ValueError("Invalid budget or contact cost") from e

def select_audience(frame, budget=1000, contact_cost=1, strategy="Predicted spending"):
    """Stable customer-ID tie-breaking makes displayed and exported selections equal."""
    f = frame.sort_values("customer_id", kind="stable").copy()
    if f.customer_id.duplicated().any():
        raise ValueError("Select one scoring date and horizon before building an audience.")
    k = capacity(budget, contact_cost, len(f))
    if strategy == "Predicted spending":
        f = f.sort_values("predicted_spending", ascending=False, kind="stable")
    elif strategy == "Historical spending":
        f = f.sort_values("historical_score", ascending=False, kind="stable")
    elif strategy == "Recency":
        f = f.sort_values("recency_days", kind="stable")
    elif strategy == "Seeded random":
        f = f.iloc[np.random.default_rng(42).permutation(len(f))]
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    f = f.head(k).copy()
    f.insert(0, "audience_rank", np.arange(1, len(f)+1))
    return f

def compare_audiences(frame, budget=1000, contact_cost=1):
    selected = select_audience(frame,budget,contact_cost)
    ids = set(selected.customer_id)
    total = frame.actual_spending.sum(min_count=1)
    rows = []
    for strategy in ["Predicted spending","Historical spending","Recency","Seeded random"]:
        a = select_audience(frame,budget,contact_cost,strategy)
        covered = a.actual_spending.sum(min_count=1) if len(a) else 0.0
        rows.append({"strategy":strategy,"contacts":len(a),"cost":float(Decimal(str(contact_cost))*len(a)),"actual_spending_covered":covered,"coverage_fraction":covered/total if total else np.nan,"overlap_with_predicted":len(ids & set(a.customer_id))/len(ids) if ids else 0.0})
    return pd.DataFrame(rows), selected

def export_selection(selection):
    return selection.to_csv(index=False).encode("utf-8")
