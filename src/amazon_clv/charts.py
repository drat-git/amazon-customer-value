"""Publication figures generated only from the saved run tables."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter, FuncFormatter

NAVY="#142D42"
TEAL="#087E83"
ORANGE="#E89B3C"

def build_charts(run):
    run=Path(run)
    out=run/"charts"
    out.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"text.parse_math":False,"axes.spines.top":False,"axes.spines.right":False,"axes.labelcolor":NAVY,"text.color":NAVY,"axes.titleweight":"bold","figure.facecolor":"white","savefig.facecolor":"white"})
    def save(fig,name):
        fig.tight_layout(pad=1.7)
        fig.savefig(out/f"{name}.png",dpi=220,bbox_inches="tight")
        fig.savefig(out/f"{name}.pdf",bbox_inches="tight")
        plt.close(fig)
    tx=pd.read_parquet(run/"transactions.parquet",columns=["customer_id","date","value_cents","is_gift"])
    monthly=tx.assign(month=tx.date.dt.to_period("M").dt.to_timestamp()).groupby("month").value_cents.sum()/100
    fig,ax=plt.subplots(figsize=(10,4.1))
    ax.plot(monthly.index,monthly/1e6,color=TEAL,lw=2)
    ax.set(title="Recorded purchase value through October 2022",ylabel="Purchase value ($ millions)",xlabel="Purchase month")
    ax.axvline(pd.Timestamp("2021-01-01"),ls="--",lw=1,color=ORANGE)
    ax.axvline(pd.Timestamp("2022-01-01"),ls="--",lw=1,color=ORANGE)
    save(fig,"monthly_spending")
    totals=tx.groupby("customer_id",observed=True).value_cents.sum().sort_values(ascending=False)
    curve=np.r_[0,totals.cumsum().to_numpy()/totals.sum()]
    population=np.linspace(0,1,len(curve))
    pd.DataFrame({"customer_fraction":population,"spending_fraction":curve}).to_csv(run/"concentration.csv",index=False)
    fig,ax=plt.subplots(figsize=(9,4.2))
    ax.plot(population,curve,color=TEAL,lw=2,label="Ranked by recorded spending")
    ax.plot([0,1],[0,1],color="#A6B5C0",ls="--",label="Equal spending")
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set(title="Purchase value concentrates among a minority of accounts",xlabel="Share of customers, highest spending first",ylabel="Share of recorded purchase value")
    ax.legend(frameon=False,loc="lower right")
    save(fig,"concentration")
    metrics=pd.read_csv(run/"test_metrics.csv")
    selected=metrics.loc[metrics.selected]
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for h,ax in zip([90,180],axes):
        m=metrics.loc[metrics.horizon.eq(h)]
        keep=m.model.str.startswith("trailing") | m.selected
        pivot=m.loc[keep].pivot(index="model",columns="scoring_date",values="rmse")
        pivot.plot.bar(ax=ax,color=[TEAL,ORANGE],rot=15)
        ax.set(title=f"{h}-day forecasts",ylabel="RMSE ($)",xlabel="Model")
        ax.legend(title="Scoring date",frameon=False,fontsize=9)
    fig.suptitle("Test errors for selected models and spending baselines",fontsize=15,y=1.02)
    save(fig,"model_errors")
    cal=pd.read_csv(run/"calibration.csv")
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for h,ax in zip([90,180],axes):
        f=cal.loc[cal.horizon.eq(h)]
        high=max(f.actual_mean.max(),f.predicted_mean.max())
        for d,g in f.groupby("scoring_date"):
            ax.plot(g.predicted_mean,g.actual_mean,marker="o",label=d)
        ax.plot([0,high],[0,high],color="#A6B5C0",ls="--",label="Perfect calibration")
        ax.set(title=f"{h}-day calibration",xlabel="Mean predicted spending ($)",ylabel="Mean actual spending ($)")
        ax.legend(frameon=False,fontsize=8)
    save(fig,"calibration")
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for h,ax in zip([90,180],axes):
        m=metrics.loc[metrics.horizon.eq(h)]
        m=m.loc[m.model.str.startswith("trailing") | m.selected]
        m.pivot(index="model",columns="scoring_date",values="capture_20").plot.bar(ax=ax,color=[TEAL,ORANGE],rot=15)
        ax.set(title=f"{h}-day top-20% capture",xlabel="Model",ylabel="Share of actual spending captured",ylim=(0,1))
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.legend(frameon=False,fontsize=8)
    save(fig,"ranking_capture")
    fig,axes=plt.subplots(1,2,figsize=(10,4.2))
    for measure,ax in zip(["wape","normalized_rmse"],axes):
        selected.pivot(index="scoring_date",columns="horizon",values=measure).plot.bar(ax=ax,color=[TEAL,ORANGE],rot=0)
        ax.set(title="WAPE" if measure=="wape" else "RMSE / mean actual spending",ylabel="Error ratio",xlabel="Scoring date")
        ax.legend(title="Horizon (days)",frameon=False)
    save(fig,"horizon_comparison")
    market=pd.read_csv(run/"marketing_comparison.csv")
    f=market.loc[market.scoring_date.eq("2022-01-01")]
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for h,ax in zip([90,180],axes):
        g=f.loc[f.horizon.eq(h)]
        ax.barh(g.strategy,g.coverage_fraction,color=[TEAL,"#60788C",ORANGE,"#B5C3CC"])
        ax.invert_yaxis()
        ax.set(title=f"{h}-day spending coverage",xlabel="Actual future spending covered",xlim=(0,1))
        ax.xaxis.set_major_formatter(PercentFormatter(1))
    fig.suptitle("Illustrative $1,000 budget at $1 per contact · January 2022",fontsize=14,y=1.02)
    save(fig,"marketing_coverage")
    if (run/"gift_sensitivity.csv").exists():
        f=pd.read_csv(run/"gift_sensitivity.csv")
        f["analysis"]=f.analysis.map({"Primary (gift cards retained)":"Gift cards retained","Sensitivity (gift cards excluded)":"Gift cards excluded"})
        fig,axes=plt.subplots(1,2,figsize=(11,4.2))
        for h,ax in zip([90,180],axes):
            f.loc[f.horizon.eq(h)].pivot(index="scoring_date",columns="analysis",values="normalized_rmse").plot.bar(ax=ax,color=[ORANGE,TEAL],rot=0)
            ax.set(title=f"{h}-day sensitivity",ylabel="RMSE / mean actual spending",xlabel="Scoring date")
            ax.legend(frameon=False,fontsize=8)
        save(fig,"gift_sensitivity")
