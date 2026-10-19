"""Small synthetic integration run. Never use these results as portfolio evidence."""
from pathlib import Path
import numpy as np
import pandas as pd
from amazon_clv.pipeline import run

root=Path(__file__).resolve().parents[1]
out=root/"runs"/"smoke"
out.parent.mkdir(exist_ok=True)
rng=np.random.default_rng(42)
rows=[]
for customer in range(12):
    for d in pd.date_range("2018-01-01","2022-10-01",freq="MS"):
        if rng.random()<.7:
            rows.append({"Survey ResponseID":f"synthetic_{customer:02}","Order Date":d.strftime("%Y-%m-%d"),"Purchase Price Per Unit":f"{rng.uniform(1,100):.2f}","Quantity":1,"ASIN/ISBN (Product Code)":f"P{customer%3}","Category":"BOOK" if customer%2 else "GROCERY","Title":"Synthetic test item","Shipping Address State":"NY"})
fixture=root/"runs"/"synthetic_smoke.csv"
pd.DataFrame(rows).to_csv(fixture,index=False)
run(fixture,out,verify_source=False,n_bootstrap=20,sensitivity=False)
assert (out/"bundle"/"models.joblib").exists()
p=pd.read_parquet(out/"customer_predictions.parquet")
assert p.actual_spending.notna().all()
assert len(p)==48
print("END-TO-END SYNTHETIC SMOKE PASSED")
