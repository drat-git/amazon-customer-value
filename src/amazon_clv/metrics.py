"""Forecast errors, calibration, spending capture, and clustered uncertainty."""
import numpy as np
import pandas as pd

def capture(y, prediction, fraction=.2):
    y, prediction = np.asarray(y), np.asarray(prediction)
    n = max(1, int(np.ceil(len(y) * fraction)))
    order = np.argsort(-prediction, kind="stable")[:n]
    return float(y[order].sum() / y.sum()) if y.sum() else np.nan

def evaluate(y, p):
    y, p = np.asarray(y, float), np.maximum(0, np.asarray(p, float))
    return {"n": len(y), "mae": float(np.mean(np.abs(y-p))),
            "rmse": float(np.sqrt(np.mean((y-p)**2))),
            "wape": float(np.abs(y-p).sum()/y.sum()) if y.sum() else np.nan,
            "normalized_rmse": float(np.sqrt(np.mean((y-p)**2))/y.mean()) if y.mean() else np.nan,
            "predicted_total": float(p.sum()), "actual_total": float(y.sum()),
            "total_ratio": float(p.sum()/y.sum()) if y.sum() else np.nan,
            "capture_10": capture(y,p,.1), "capture_20": capture(y,p,.2)}

def calibration(frame):
    f = frame.sort_values(["predicted_spending", "customer_id"], kind="stable").copy()
    f["decile"] = np.minimum(10, (np.arange(len(f)) * 10 // max(len(f), 1)) + 1)
    return f.groupby("decile", observed=True).agg(n=("customer_id","size"), predicted_mean=("predicted_spending","mean"), actual_mean=("actual_spending","mean")).reset_index()

def bootstrap(frame, n_resamples=500, seed=42):
    """Sample customer IDs with replacement, retaining all repeated dates per ID."""
    ids = frame.customer_id.unique()
    groups = {k: v.index.to_numpy() for k,v in frame.reset_index(drop=True).groupby("customer_id", sort=True)}
    f = frame.reset_index(drop=True)
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n_resamples):
        sampled = rng.choice(ids, size=len(ids), replace=True)
        ix = np.concatenate([groups[k] for k in sampled])
        a = f.iloc[ix]
        r = evaluate(a.actual_spending, a.predicted_spending)
        r["capture_20_gain_pp"] = 100 * (r["capture_20"] - capture(a.actual_spending, a.historical_score, .2))
        rows.append(r)
    b = pd.DataFrame(rows)
    point = evaluate(f.actual_spending, f.predicted_spending)
    point["capture_20_gain_pp"] = 100 * (point["capture_20"] - capture(f.actual_spending, f.historical_score, .2))
    return [{"metric": c, "estimate": point[c], "lower_95": b[c].quantile(.025), "upper_95": b[c].quantile(.975), "resamples": n_resamples, "customers": len(ids)} for c in ["mae","rmse","wape","normalized_rmse","total_ratio","capture_10","capture_20","capture_20_gain_pp"]]
