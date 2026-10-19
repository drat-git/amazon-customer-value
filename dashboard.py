"""Historical demonstration. Read saved analytical outputs, never retrain."""
from pathlib import Path
import os
import json
import sys
import pandas as pd
import streamlit as st
sys.path.insert(0,str(Path(__file__).resolve().parent/"src"))
from amazon_clv.marketing import compare_audiences,export_selection

ROOT=Path(__file__).resolve().parent
DEFAULT_RUN=ROOT/"runs"/"main" if (ROOT/"runs"/"main"/"manifest.json").exists() else ROOT/"demo"
RUN=Path(os.environ.get("AMAZON_CLV_RUN",DEFAULT_RUN))
st.set_page_config(page_title="Amazon Customer Value Lab",page_icon="📈",layout="wide")

@st.cache_data
def load_table(path,stamp):
    return pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path)

def table(name):
    p=RUN/name
    return load_table(str(p),p.stat().st_mtime_ns)

st.title("Amazon Customer Value Lab")
st.caption("HISTORICAL DEMONSTRATION · Purchase histories from 2018 through October 2022 · Recorded customer purchase value")
if not (RUN/"manifest.json").exists():
    st.info("Run the analytical pipeline first. See the README for the command, or set AMAZON_CLV_RUN to a completed run.")
    st.stop()
model_info=json.loads((RUN/"bundle"/"manifest.json").read_text())
public_demo=(RUN/"daily_history.parquet").exists()
pred=table("customer_predictions.parquet")
pred["scoring_date"]=pd.to_datetime(pred.scoring_date).dt.strftime("%Y-%m-%d")
st.sidebar.header("Historical demonstration")
view=st.sidebar.radio("View",["Overview","Model performance","Customer explorer","Marketing prioritization","Methodology"])
date=st.sidebar.selectbox("Historical scoring date",sorted(pred.scoring_date.unique()),index=0)
horizon=st.sidebar.selectbox("Forecast horizon (days)",[90,180])
f=pred.loc[pred.scoring_date.eq(date)&pred.horizon.eq(horizon)].copy()
st.sidebar.caption(f"Frozen model: {model_info['models'][str(horizon)]['name']}\n\nLabels available before 2022-01-01. Same fitted models at both test dates.")
if public_demo:
    st.sidebar.caption("Public portfolio demo · Saved real-data forecasts · Display account aliases and daily purchase totals")
st.subheader(f"{view} · {date} · {horizon}-day horizon")
st.info("Historical demonstration. Customer-value coverage under a contact budget describes recorded spending among selected accounts. Campaign uplift, profit CLV, and causal marketing ROI require additional data.")

if view=="Overview":
    st.write("How well can past purchase behavior forecast the next 90 or 180 days of spending, and which accounts cover the most future purchase value within an illustrative contact budget?")
    cols=st.columns(4)
    cols[0].metric("Eligible accounts",f"{len(f):,}")
    cols[1].metric("Forecast spending",f"${f.predicted_spending.sum():,.0f}")
    cols[2].metric("Recorded future spending",f"${f.actual_spending.sum():,.0f}")
    metrics=table("test_metrics.csv")
    m=metrics.loc[metrics.scoring_date.eq(date)&metrics.horizon.eq(horizon)&metrics.selected].iloc[0]
    cols[3].metric("Top 20% spending capture",f"{m.capture_20:.1%}")
    st.write(f"Selected model: **{m['model']}**. RMSE **\\${m.rmse:,.2f}**, MAE **\\${m.mae:,.2f}**, WAPE **{m.wape:.1%}**. The 180-day forecast is at least the 90-day forecast for every customer.")
    st.image(str(RUN/"charts"/"concentration.png"),caption="Full retained observation window. Ranking uses observed spending for this descriptive chart.")
    st.write("Accounts come from a retrospective sample of approximately 5,000 consenting U.S. participants. Shared accounts and survival to recruitment limit interpretation.")

elif view=="Model performance":
    m=table("test_metrics.csv")
    st.dataframe(m.loc[m.scoring_date.eq(date)&m.horizon.eq(horizon),["model","selected","mae","rmse","wape","normalized_rmse","actual_total","predicted_total","capture_10","capture_20","adjustment_rate"]],hide_index=True)
    cal=table("calibration.csv")
    c=cal.loc[cal.scoring_date.eq(date)&cal.horizon.eq(horizon)].set_index("decile")
    st.write("Calibration by predicted spending decile (10 is highest)")
    st.line_chart(c[["predicted_mean","actual_mean"]])
    ci=table("bootstrap_intervals.csv")
    st.write("95% customer-bootstrap intervals, conditional on the frozen models")
    st.dataframe(ci.loc[ci.horizon.eq(horizon)&ci.scope.eq(date)],hide_index=True)
    st.caption("500 resamples. The combined-date intervals keep all observations of each sampled customer together. Overlapping windows remain dependent.")
    seg=table("segment_errors.csv")
    st.write("Errors in descriptive history groups")
    st.dataframe(seg.loc[seg.scoring_date.eq(date)&seg.horizon.eq(horizon)],hide_index=True)
    sensitivity=table("gift_sensitivity.csv")
    st.write("Separately trained sensitivity without gift-card/reload titles")
    st.dataframe(sensitivity.loc[sensitivity.scoring_date.eq(date)&sensitivity.horizon.eq(horizon),["analysis","model","n","rmse","wape","normalized_rmse","capture_20"]],hide_index=True)

elif view=="Customer explorer":
    segment=st.selectbox("Descriptive customer segment",["All"]+sorted(f.segment.unique()))
    customers=f if segment=="All" else f.loc[f.segment.eq(segment)]
    customer=st.selectbox("Account ID",customers.sort_values("predicted_spending",ascending=False).customer_id.tolist())
    one=f.loc[f.customer_id.eq(customer)].iloc[0]
    a,b,c=st.columns(3)
    a.metric("Forecast spending",f"${one.predicted_spending:,.2f}")
    b.metric("Recorded future spending",f"${one.actual_spending:,.2f}")
    c.metric("Days since last purchase",int(one.recency_days))
    both=pred.loc[pred.scoring_date.eq(date)&pred.customer_id.eq(customer)]
    st.dataframe(both[["horizon","model_name","predicted_spending","actual_spending","coherence_adjusted","segment"]],hide_index=True)
    tx=table("daily_history.parquet" if public_demo else "transactions.parquet")
    history=tx.loc[tx.customer_id.astype(str).eq(customer)&tx.date.lt(pd.Timestamp(date))].copy()
    history["purchase_value"]=history.value_cents/100
    daily=history.groupby("date").purchase_value.sum()
    st.line_chart(daily.rename("Historical purchase value ($)"))
    st.caption("Only purchases before the selected scoring date appear below. Distinct purchase days are observable; distinct order counts are unavailable.")
    if public_demo:
        st.caption("The public demo shows daily totals with display account aliases. Item titles, product IDs, shipping states, and original survey IDs are omitted.")
        st.dataframe(history[["date","quantity","purchase_value"]].sort_values("date",ascending=False),hide_index=True)
    else:
        st.dataframe(history[["date","title","category","quantity","purchase_value","is_gift"]].sort_values("date",ascending=False),hide_index=True)

elif view=="Marketing prioritization":
    a,b=st.columns(2)
    budget=a.number_input("Illustrative contact budget ($)",min_value=0.0,value=1000.0,step=100.0)
    cost=b.number_input("Uniform contact cost ($)",min_value=0.01,value=1.0,step=.25)
    try:
        comparison,selected=compare_audiences(f,budget,cost)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    capacity=len(selected)
    a,b,c=st.columns(3)
    a.metric("Contact capacity",f"{capacity:,}")
    b.metric("Contact cost used",f"${capacity*cost:,.2f}")
    c.metric("Actual future spending covered",f"${selected.actual_spending.sum():,.2f}")
    st.write("Customer-value coverage under a contact budget")
    st.dataframe(comparison,hide_index=True)
    st.bar_chart(comparison.set_index("strategy")[["coverage_fraction"]])
    st.caption("All strategies contact the same number of accounts. Historical ranking uses trailing 365-day spending. Random ranking uses seed 42. Overlap is relative to the predicted-spending audience.")
    st.dataframe(selected,hide_index=True)
    st.download_button("Download displayed customer selection",data=export_selection(selected),file_name=f"audience_{date}_{horizon}d.csv",mime="text/csv")

else:
    audit=json.loads((RUN/"data_audit.json").read_text())
    st.write("**Source:** Berke et al., Open e-commerce 1.0, Harvard Dataverse, version 1.0, CC0 1.0. [Dataset](https://doi.org/10.7910/DVN/YGLYDY) · [Data descriptor](https://www.nature.com/articles/s41597-024-03329-6).")
    st.write("Monthly snapshots begin January 2019. Eligible accounts have at least one prior valid purchase. Features use dates strictly before scoring. Targets sum integer-cent purchase value in [scoring date, scoring date + horizon). Zero purchase outcomes remain present. Targets remain unavailable without a fully observed window.")
    st.write("Category mappings use only 2018 history. Standardization fits inside each training fold. Customer identifiers and later survey responses never enter predictive features. All validation training labels finish before the validation date. Final models use labels available before January 2022 and stay fixed for January and May tests.")
    st.write("The main analysis retains gift cards. Sensitivity excludes titles matching gift card, gift code, digital code, or Amazon reload, case insensitive. Identical rows remain because no order ID exists.")
    st.write("Recorded purchase value differs from Amazon revenue and profit. Returns, margins, treatment assignment, and campaign responses are unavailable. Predictive associations do not establish causal drivers. The cohort favors established accounts active at recruitment.")
    st.json(audit)
