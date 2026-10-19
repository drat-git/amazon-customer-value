"""Create a ten-page analytical report from the single release evidence file."""
from pathlib import Path
import json
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor,white
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/"reports"/"release_data.json").read_text())
OUT=ROOT/"reports"/"amazon_customer_value_report.pdf"
W,H=A4
NAVY=HexColor("#142D42"); TEAL=HexColor("#087E83"); MUTED=HexColor("#526878"); LIGHT=HexColor("#E7EFF2")
c=canvas.Canvas(str(OUT),pagesize=A4)
c.setTitle("Amazon Customer Value Prediction and Marketing Prioritization")
c.setAuthor("Amazon CLV Portfolio")
body=ParagraphStyle("body",fontName="Helvetica",fontSize=10.4,leading=15.2,textColor=NAVY,spaceAfter=10)
small=ParagraphStyle("small",parent=body,fontSize=8.5,leading=12)
heading=ParagraphStyle("heading",parent=body,fontName="Helvetica-Bold",fontSize=15,leading=19,spaceAfter=9)
y=0; page=0

def start(title,kicker="HISTORICAL DEMONSTRATION"):
    global y,page
    if page: c.showPage()
    page+=1
    c.setFillColor(TEAL); c.setFont("Helvetica-Bold",8.5); c.drawString(46,H-39,kicker)
    c.setFillColor(NAVY); c.setFont("Helvetica-Bold",23); c.drawString(46,H-76,title)
    c.setStrokeColor(LIGHT); c.line(46,48,W-46,48)
    c.setFillColor(MUTED); c.setFont("Helvetica",8)
    c.drawString(46,33,"Amazon customer value · real-data portfolio · October 18, 2026")
    c.drawRightString(W-46,33,f"{page:02} / 10")
    y=H-102

def text(s,style=body):
    global y
    p=Paragraph(s,style)
    _,height=p.wrap(W-92,y-64)
    if y-height<63: raise ValueError(f"Page {page} content overflows at {s[:70]}")
    p.drawOn(c,46,y-height)
    y-=height+style.spaceAfter

def sub(s): text(escape(s),heading)
def table(rows,widths=None,size=9):
    global y
    if widths is None: widths=[(W-92)/len(rows[0])]*len(rows[0])
    style=ParagraphStyle("cell",parent=body,fontSize=size,leading=size+3,spaceAfter=0)
    values=[[Paragraph(escape(str(v)),style) for v in row] for row in rows]
    t=Table(values,colWidths=widths,hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),LIGHT),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("BOTTOMPADDING",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),8),("LEFTPADDING",(0,0),(-1,-1),7),("VALIGN",(0,0),(-1,-1),"TOP"),("LINEBELOW",(0,0),(-1,0),.8,TEAL),("LINEBELOW",(0,1),(-1,-1),.3,LIGHT)]))
    _,h=t.wrap(W-92,y-64)
    if y-h<63: raise ValueError(f"Page {page} table overflow")
    t.drawOn(c,46,y-h);y-=h+15

def chart(name,height=215):
    global y
    p=ROOT/"runs"/"main"/"charts"/f"{name}.png"
    im=ImageReader(str(p)); iw,ih=im.getSize(); width=min(W-92,height*iw/ih);h=width*ih/iw
    if y-h<63: raise ValueError(f"Page {page} chart overflow")
    c.drawImage(im,46+(W-92-width)/2,y-h,width,h,mask="auto");y-=h+12

money=lambda v:f"${v:,.0f}"
pct=lambda v:f"{v:.1%}"
metrics=D["selected_metrics"]
audit=D["audit"]

start("Customer spending forecasts","AMAZON CUSTOMER VALUE PREDICTION")
text("<b>90-day and 180-day purchase value for marketing prioritization</b>",heading)
text("This project predicts recorded future purchase value from prior transaction history and evaluates customer selection under a uniform contact budget. It uses a consented retrospective cohort and a local, reproducible Python pipeline.")
sub("What the untouched tests show")
table([["Scoring date","Days","RMSE","WAPE","Top 20% capture"]]+[[r["scoring_date"],r["horizon"],money(r["rmse"]),pct(r["wape"]),pct(r["capture_20"])] for r in metrics],[100,42,95,80,186-0])
text("Validation selected histogram gradient boosting for 90 days and Ridge with alpha 100 for 180 days. Both final models use labels available before January 2022 and remain fixed for the January and May tests.")
text("The selected models improve RMSE against the trailing-year baseline on all four test evaluations. Their top-20% capture gains over raw historical-spending ranking are modest: <b>0.28 to 0.99 percentage points</b>. The January 180-day model overpredicts aggregate spending by <b>25.3%</b>.")
text("A longer horizon has better normalized errors in these tests, while the 90-day model has stronger aggregate calibration. Horizon choice should follow the decision cadence and these tradeoffs. Smaller short-horizon dollar error alone is insufficient.")
text("<b>Decision scope:</b> customer-value coverage under a contact budget. Campaign uplift, incremental revenue, profit CLV, and causal marketing ROI require additional data.",small)

start("Data provenance and quality")
text("Open e-commerce 1.0 contains crowdsourced Amazon purchase histories from consenting U.S. participants. Harvard Dataverse publishes version 1.0 under CC0 1.0. The mirror's bytes match the original release's MD5.")
table([["Audit item","Measured result"],["Raw file",f"{audit['source_rows']:,} rows / {audit['source_customers']:,} accounts"],["Retained common window",f"{audit['valid_rows']:,} rows / {audit['valid_customers']:,} accounts"],["Purchase value",money(audit["total_value_cents"]/100)],["Later dates excluded",f"{sum(audit['exclusions_sequential'].values()):,} rows"],["Identical rows retained",f"{audit['identical_rows_retained']:,}"],["Gift/reload title matches",f"{audit['gift_rows']:,} rows"]],[215,W-307])
text("Valid transactions span January 1, 2018 through October 31, 2022. The raw file extends to August 2024, including one anomalous 2024 record. The common exclusive end of November 1, 2022 avoids treating uneven later exports as equivalent coverage.")
text("No rows failed customer, date, price, or quantity checks in this file. Missing category, title, product, and state values become explicit UNKNOWN descriptions. Unit prices use Decimal half-up cent rounding, quantities must be positive integers, and value aggregates in integer cents. Equal rows remain because no order ID resolves duplicates.")
chart("concentration",180)
text("MD5: "+audit["md5"],small)
text('Sources: Berke et al. (2024), Scientific Data 11, 491. <link href="https://www.nature.com/articles/s41597-024-03329-6" color="#087E83">doi:10.1038/s41597-024-03329-6</link>. Dataset: <link href="https://doi.org/10.7910/DVN/YGLYDY" color="#087E83">doi:10.7910/DVN/YGLYDY</link>. Exact metadata and SHA256 accompany this project.',small)

start("Customer snapshots and targets")
text("Monthly scoring dates begin January 2019. Eligibility requires at least one valid purchase before scoring. One account-date is one modeling observation. Accounts repeat over time, so observations and overlapping forecast windows are dependent.")
table([["Component","Contract"],["Historical features","Transaction date strictly before scoring date"],["90-day target","Sum over [scoring date, scoring date + 90 days)"],["180-day target","Sum over [scoring date, scoring date + 180 days)"],["No future purchases","Recorded zero if the entire window is observed"],["Incomplete future window","Unavailable target, never an assumed zero"]],[150,W-242])
text("A January 1 purchase enters the target, while December 31 remains historical. January 1, 2022's 90-day target ends April 1 exclusively. Its 180-day target ends June 30 exclusively. These are fixed day counts, not calendar-month approximations.")
sub("Purchase-derived features")
text("Recency and observed history length describe engagement and available tenure. For 30, 90, 180, and 365 days, features measure spending, quantities, distinct purchase days, product/category diversity, and spending per purchase day. Trends compare recent and preceding spending. Month sine/cosine features encode seasonality.")
text("A frozen vocabulary learns the top 12 categories by 2018 spending, before every snapshot. UNKNOWN handles missing categories and OTHER handles new categories. Ridge standardization fits only on each fold's training examples. Identifiers and later-collected survey answers never enter predictive inputs.")
text("The package shares the same feature function and prediction bundle between training and batch scoring. Tests append future purchases and check that all earlier features remain identical.",small)

start("Label-aware chronological validation")
text("A historical feature row can still leak if its future label was unavailable at the validation date. The pipeline explicitly requires every training target's exclusive end to be strictly earlier than its cutoff. This conservative purge protects both horizons.")
table([["Stage / horizon","Cutoff","Latest train label end","Training rows"]]+[[r["stage"].replace("_"," ")+f" / {r['horizon']}d",r["cutoff"],r["max_label_end"],f"{r['train_n']:,}"] for r in D["split_audit"]],[136,100,145,W-473],8.3)
text("Validation uses January and July 2021, with development scoring dates confined to 2019-2020. Equal weighting of the two fold RMSEs selects candidates. Once those choices freeze, final fitting can use matured 2021 examples whose labels finish before January 2022.")
text("The same fitted final bundle scores January 1 and May 1, 2022. May features legitimately incorporate purchases before May. Those observed histories can overlap January outcomes, but they never become final-model training labels.")
text("Both tests are historical demonstrations on a selected cohort. Repeated accounts and overlapping target windows prevent interpreting the two dates as independent experiments. The bootstrap preserves account clusters, with calendar-regime uncertainty still unresolved.")

start("Models and test performance")
text("Each horizon compares trailing-90 and trailing-365 spending rates, Ridge alpha 0.1/1/10/100, and histogram boosting at learning rate 0.05/0.1 with 15/31 leaves and 300 iterations. Random internal early stopping is disabled. Seed: 42.")
text("Choose lowest mean validation RMSE. Within 1%, prefer top-20% capture, then simplicity. ML must improve the best baseline's RMSE to qualify. Clamp forecasts at zero. Select 90 days first, then evaluate 180-day candidates after max(raw180, selected90). Apply that same constraint at test and scoring.")
chart("model_errors",225)
table([["Date","Days","Selected model","RMSE vs 365d baseline"]]+[[r["scoring_date"],r["horizon"],r["model"],f"{100*(1-r['rmse']/next(x['rmse'] for x in D['all_metrics'] if x['horizon']==r['horizon'] and x['scoring_date']==r['scoring_date'] and x['model']=='trailing_365')):.1f}% lower"] for r in metrics],[100,42,155,W-389],8.5)
text("For 180-day model comparisons, each candidate receives the same horizon-coherence adjustment. Raw historical-spending ranking remains a separate benchmark. No test results feed model selection.",small)

start("Calibration and spending capture")
chart("calibration",225)
text("Deciles compare mean predicted and actual spending within ranked groups. A model can rank valuable accounts reasonably well while overstating their dollar value. Aggregate predicted/actual ratios expose an important shortcoming here.")
table([["Date","Days","Predicted / actual total","Top-20% gain vs history"]]+[[r["scoring_date"],r["horizon"],f"{r['total_ratio']:.3f}",f"{r['capture_20_gain_pp']:+.2f} pp"] for r in metrics],[100,42,180,W-414],9)
text("The selected rankings capture about 53% of future spending in the top fifth of accounts. Most of that concentration already appears in historical-spending rankings. The additional gain from modeling is small and should be presented alongside uncertainty, not as a large marketing lift.")
text("The 180-day adjustment raises 1.34% of January forecasts and 4.38% of May forecasts. It protects arithmetic consistency, but does not guarantee calibration. Predictive associations in the saved permutation table do not establish causal drivers.")

start("Horizon comparison and uncertainty")
chart("horizon_comparison",200)
text("WAPE divides absolute error by actual dollars. Normalized RMSE divides RMSE by mean actual spending. Both normalize the spending scale and favor the 180-day horizon here. The 90-day model's aggregate ratios are closer to one. A business horizon depends on whether ranking, amount calibration, or planning cadence matters most.")
table([["Days","Pooled metric","Estimate","95% customer-bootstrap interval"]]+[[r["horizon"],r["metric"],f"{r['estimate']:.3f}",f"[{r['lower_95']:.3f}, {r['upper_95']:.3f}]"] for r in D["uncertainty"] if r["scope"]=="Both test dates" and r["metric"] in ["rmse","wape","capture_20","capture_20_gain_pp"]],[45,150,80,W-367],8.4)
text("500 resamples draw accounts with replacement, retaining every repeated test observation for a sampled account. Percentile intervals condition on the frozen models and chosen cohort. They do not refit models or account for all model-selection, source-coverage, or future-time uncertainty. Pooled windows can count the same purchase twice and are not unique annual spending.",small)

start("Marketing prioritization")
text("Illustrative budget: $1,000. Uniform contact cost: $1. Capacity equals floor(budget / cost), capped at eligible accounts. All strategies contact the same 1,000 accounts. The simulator compares predicted spending with historical spending, recency, and seed-42 random ranking.")
chart("marketing_coverage",215)
table([["Days","Strategy","Covered future value","Coverage"]]+[[r["horizon"],r["strategy"],money(r["actual_spending_covered"]),pct(r["coverage_fraction"])] for r in D["marketing"] if r["scoring_date"]=="2022-01-01"],[40,155,150,W-437],8.4)
text("Historical ranking overlaps 87.0% of the 90-day predicted audience. The dashboard displays and downloads the same ranked rows. Zero budgets select nobody, oversized budgets select all, and invalid budgets/costs reject. Decimal floor arithmetic protects contact capacity at cent boundaries.",small)
text("<b>Business interpretation:</b> customer-value coverage under a contact budget. The accounts might have purchased anyway. Causal campaign return requires randomized treatment/control outcomes and margins.",small)

start("Sensitivity and customer examples")
chart("gift_sensitivity",185)
text("The primary retains 39,006 title-matched gift/reload rows. The separately rerun sensitivity excludes the documented terms and can change targets, cohort eligibility, and model selection. Normalized RMSE becomes slightly worse in all four sensitivity evaluations, despite smaller dollar RMSE. Amount scales matter.")
table([["Date","Days","No-gift selected model","Normalized RMSE"]]+[[r["scoring_date"],r["horizon"],r["model"],f"{r['normalized_rmse']:.3f}"] for r in D["sensitivity"] if r["analysis"].startswith("Sensitivity")],[100,42,200,W-434],8.5)
sub("January 2022 account examples")
table([["Forecast percentile example","Days","Predicted","Actual"]]+[[r["example"],r["horizon"],money(r["predicted_spending"]),money(r["actual_spending"])] for r in D["examples"]],[205,45,115,W-457],8.5)
text("Examples use forecast ranks, not favorable outcomes. January 90-day group RMSE is $211 for 35 short-history accounts, $112 for 317 inactive accounts, and $1,207 for 500 high historical spenders. Their WAPE is 103.8%, 183.9%, and 46.6%, respectively. Small dollar errors can hide large relative errors in low-spending groups. Groups overlap and small groups are unstable.",small)

start("Limitations and reproducibility")
sub("What these results can support")
text("Recorded fixed-horizon spending forecasts and retrospective ranking comparisons for established accounts in this cohort. They support discussing which customers cover more observed future value within an assumed contact budget.")
sub("What remains unresolved")
text("The sample is consent-selected and favors established accounts still active at recruitment. Accounts can be shared. History starts in 2018 and does not reveal true tenure. Common October 2022 coverage follows the source study but transaction absence alone cannot prove complete per-account exports. The data omit usable campaign assignments, margins, true order IDs, and resolved return adjustments. Behavior in later years can differ.")
text("Customer spending is not Amazon net revenue or profit. Predictive importance measures association. Neither spending coverage nor ranking gain establishes response to marketing, incremental revenue, causal ROI, or an optimal offer.")
sub("Reproduce and inspect")
text("Create Python 3.12 environment, install requirements.lock.txt, then install the package. Run python -m amazon_clv run with the verified CSV and a new output directory. Run python -m amazon_clv score with a historical date and saved bundle. The README supplies exact commands. Four clean-kernel notebooks explain data quality, features, modeling, and marketing. Tests protect temporal boundaries, serialization, and budget exports.")
text("The release includes source hashes, exclusion and split audits, frozen selections, model bundles, predictions, metric tables, calibration, bootstrap intervals, gift sensitivity, charts, a local Streamlit dashboard, data dictionary, model card, chronological work log, and interview guide.")
sub("References")
text('Berke et al. (2024). Open e-commerce 1.0. Scientific Data 11, 491. <link href="https://www.nature.com/articles/s41597-024-03329-6" color="#087E83">nature.com/articles/s41597-024-03329-6</link><br/>Harvard Dataverse v1.0, CC0 1.0. <link href="https://doi.org/10.7910/DVN/YGLYDY" color="#087E83">doi.org/10.7910/DVN/YGLYDY</link><br/>Streamlit caching documentation. <link href="https://docs.streamlit.io/develop/concepts/architecture/caching" color="#087E83">docs.streamlit.io/develop/concepts/architecture/caching</link><br/>All figures and measured findings: this project&#39;s saved original-data run, seed 42.',small)
assert page==10
c.save()
print(OUT)
