# Data dictionary

## Source columns

| Original | Normalized | Definition and treatment |
|---|---|---|
| Survey ResponseID | customer_id | Trimmed account/respondent key. Required. Join/export key only, never predictive input. |
| Order Date | date | Strict YYYY-MM-DD, no time zone. Required. Restrict to 2018-01-01 <= date < 2022-11-01. |
| Purchase Price Per Unit | unit_price_cents | Positive finite Decimal rounded half up to integer cents. Values over $100 million or rounding to zero reject. |
| Quantity | quantity | Positive finite integer, at most 1 million. Fractional/missing values reject. |
| ASIN/ISBN (Product Code) | product_id | Trimmed uppercase. Missing becomes UNKNOWN. |
| Category | category | Trimmed uppercase. Missing becomes UNKNOWN. No inference from later titles. |
| Title | title | Trimmed description. Missing becomes UNKNOWN. Only used for documented gift flag and history display. |
| Shipping Address State | state | Trimmed uppercase. Missing becomes UNKNOWN. Retained for provenance, excluded from prediction. |
| Derived | value_cents | Integer unit_price_cents * integer quantity. |
| Derived | is_gift | Case-insensitive title regex: gift\s+card, gift\s+code, digital\s+code, amazon\s+reload. |

Sequential exclusions appear in `data_audit.json`. Equal rows remain. This file does not contain a reliable order identifier.

## Snapshot metadata and targets

| Field | Definition |
|---|---|
| customer_id | One account eligible from at least one purchase strictly before scoring date. |
| scoring_date | First of month, January 2019 through October 2022 in saved snapshots. |
| label_end_90 / label_end_180 | Exclusive end date, exactly 90/180 calendar days after scoring date. |
| target_90 / target_180 | Dollar sum in [scoring_date, label_end). Zero for no purchases within complete coverage. NaN if label_end exceeds 2022-11-01. |

## Predictive features

All histories end strictly before scoring. All monetary features use dollars, sourced from integer-cent aggregates. Missing aggregations and undefined spending-per-day values become zero. Available-history features distinguish short histories from inactivity.

| Feature | Definition |
|---|---|
| history_days | Days since first observed valid purchase. Observed tenure, not account age. |
| recency_days | Days since last valid purchase. |
| lifetime_spend | All recorded historical value since 2018. |
| lifetime_purchase_days | Number of distinct observed historical purchase dates. |
| spend_D | Dollar sum during [scoring_date-D, scoring_date), D in 30,90,180,365. |
| purchase_days_D | Distinct purchase dates in the same window. |
| quantity_D | Sum of purchased quantities in the window. |
| products_D | Distinct product codes, including explicit UNKNOWN when present. |
| categories_D | Distinct original normalized categories, including UNKNOWN. |
| spend_per_purchase_day_D | spend_D / purchase_days_D; zero if no days. |
| observed_days_D | min(history_days, D). |
| category_share_00... | Share of trailing-365-day value in each frozen category. Top 12 categories by 2018 value, then UNKNOWN, OTHER. Exact mapping saved in category_mapping.json. Zero shares for no trailing-year spending. |
| spend_trend_30 | spend_30 minus half of (spend_90 - spend_30). Recent 30 days against preceding 60-day monthly-equivalent rate. |
| spend_trend_90 | spend_90 minus (spend_180 - spend_90). |
| spend_trend_180 | spend_180/180 minus (spend_365 - spend_180)/185. Daily-rate comparison. |
| month_sin, month_cos | sin/cos(2*pi*calendar_month/12). |

## Prediction export

| Field | Definition |
|---|---|
| horizon | 90 or 180 days. |
| predicted_spending | Nonnegative dollar forecast. 180-day forecast >= 90-day forecast. |
| raw_predicted_spending | Clamped forecast before cross-horizon adjustment. |
| actual_spending | Same-window observed target when fully available, otherwise blank. |
| coherence_adjusted | True only when raw 180-day prediction was raised to the 90-day forecast. |
| model_name | Selected candidate specification identifier. |
| model_version | Package/run identity including source SHA256 prefix. |
| historical_score | Trailing-365-day spending for historical ranking. |
| segment | Short history if history_days<90, else Inactive if recency_days>=180, else Established. Dashboard segments are mutually exclusive by this precedence. Evaluation error groups can overlap. |

Customer prediction files also carry customer_id, scoring_date, recency_days, history_days, spend_90, and purchase_days_365. Audience exports add audience_rank. Predicted dollars retain more decimals than currency displays so exported ranking reproduces the saved model.
