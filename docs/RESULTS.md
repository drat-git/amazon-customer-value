# Measured results

Historical demonstration. All values below derive from the saved real-data run. Model choices froze before 2022 test evaluation.

Source MD5: `3549d72735b1211ab009ff0177b94bd9` (verified). 1,737,058 retained rows, 5,015 accounts, $41,258,953.83 recorded value. 113,659 rows excluded, all for dates after October 31, 2022. 10,911 identical rows retained. 39,006 title-matched gift rows retained in primary.

## Frozen choices

- 90 days: `hgb_0.05_15`.
- 180 days: `ridge_100`.
- Category vocabulary from 2018 only. Final training labels finish before 2022-01-01. Same fitted bundle at both test dates.

## Untouched 2022 evaluation

| Date | Days | Accounts | MAE | RMSE | WAPE | Normalized RMSE | Top-20% capture | Gain vs historical ranking |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022-01-01 | 90 | 4,991 | $290.28 | $528.42 | 58.9% | 1.072 | 53.4% | +0.28 pp |
| 2022-05-01 | 90 | 5,004 | $291.49 | $553.41 | 51.4% | 0.975 | 53.6% | +0.99 pp |
| 2022-01-01 | 180 | 4,991 | $557.29 | $886.97 | 55.0% | 0.876 | 53.2% | +0.99 pp |
| 2022-05-01 | 180 | 5,004 | $503.51 | $869.90 | 46.3% | 0.800 | 52.9% | +0.59 pp |

Historical ranking uses unadjusted trailing-365-day spending. Candidate 180-day baseline predictions also receive the shared horizon-coherence constraint, so their ranking can differ from raw historical ranking.

## Total calibration and coherence

| Date | Days | Predicted total | Actual total | Ratio | Adjusted forecasts |
|---|---:|---:|---:|---:|---:|
| 2022-01-01 | 90 | $2,868,292.56 | $2,460,953.61 | 1.166 | 0.00% |
| 2022-05-01 | 90 | $2,739,583.67 | $2,840,185.41 | 0.965 | 0.00% |
| 2022-01-01 | 180 | $6,336,727.45 | $5,055,762.42 | 1.253 | 1.34% |
| 2022-05-01 | 180 | $5,904,427.92 | $5,440,171.86 | 1.085 | 4.38% |

## Conditional customer-bootstrap uncertainty

500 resamples. The pooled dates repeat customers and overlap forecast windows. All rows from a sampled customer stay together. These intervals condition on fitted models and do not fix selection or temporal bias.

| Days | Metric | Estimate | 95% interval |
|---:|---|---:|---:|
| 90 | mae | 290.8842 | [280.4426, 300.6829] |
| 90 | rmse | 541.0762 | [499.9903, 586.2502] |
| 90 | wape | 0.5484 | [0.5346, 0.5621] |
| 90 | normalized_rmse | 1.0202 | [0.9619, 1.0893] |
| 90 | total_ratio | 1.0579 | [1.0361, 1.0781] |
| 90 | capture_10 | 0.3503 | [0.3372, 0.3647] |
| 90 | capture_20 | 0.5333 | [0.5206, 0.5463] |
| 90 | capture_20_gain_pp | 0.5552 | [0.0297, 1.0275] |
| 180 | mae | 530.3611 | [514.1157, 546.8095] |
| 180 | rmse | 878.4669 | [825.7938, 928.1028] |
| 180 | wape | 0.5050 | [0.4912, 0.5193] |
| 180 | normalized_rmse | 0.8365 | [0.7906, 0.8849] |
| 180 | total_ratio | 1.1663 | [1.1460, 1.1870] |
| 180 | capture_10 | 0.3453 | [0.3328, 0.3596] |
| 180 | capture_20 | 0.5275 | [0.5156, 0.5400] |
| 180 | capture_20_gain_pp | 0.4661 | [0.0410, 1.0203] |

## Illustrative budget: $1,000 at $1/contact, January 2022

| Days | Strategy | Contacts | Actual spending covered | Coverage | Overlap with predicted audience |
|---:|---|---:|---:|---:|---:|
| 90 | Predicted spending | 1,000 | $1,313,621.52 | 53.4% | 100.0% |
| 90 | Historical spending | 1,000 | $1,309,821.08 | 53.2% | 87.0% |
| 90 | Recency | 1,000 | $941,112.66 | 38.2% | 46.9% |
| 90 | Seeded random | 1,000 | $500,476.93 | 20.3% | 19.9% |
| 180 | Predicted spending | 1,000 | $2,690,119.38 | 53.2% | 100.0% |
| 180 | Historical spending | 1,000 | $2,644,602.93 | 52.3% | 86.4% |
| 180 | Recency | 1,000 | $1,923,176.43 | 38.0% | 45.4% |
| 180 | Seeded random | 1,000 | $1,038,215.53 | 20.5% | 19.6% |

Covered spending is not incremental campaign revenue. The budget and contact cost are assumptions.

## Gift sensitivity

| Analysis | Date | Days | Selected model | RMSE | Normalized RMSE | Capture 20% |
|---|---|---:|---|---:|---:|---:|
| Primary (gift cards retained) | 2022-01-01 | 90 | hgb_0.05_15 | $528.42 | 1.072 | 53.4% |
| Primary (gift cards retained) | 2022-05-01 | 90 | hgb_0.05_15 | $553.41 | 0.975 | 53.6% |
| Primary (gift cards retained) | 2022-01-01 | 180 | ridge_100 | $886.97 | 0.876 | 53.2% |
| Primary (gift cards retained) | 2022-05-01 | 180 | ridge_100 | $869.90 | 0.800 | 52.9% |
| Sensitivity (gift cards excluded) | 2022-01-01 | 90 | hgb_0.05_31 | $524.97 | 1.096 | 54.2% |
| Sensitivity (gift cards excluded) | 2022-05-01 | 90 | hgb_0.05_31 | $549.61 | 0.996 | 54.3% |
| Sensitivity (gift cards excluded) | 2022-01-01 | 180 | ridge_10 | $868.24 | 0.882 | 53.7% |
| Sensitivity (gift cards excluded) | 2022-05-01 | 180 | ridge_10 | $857.36 | 0.809 | 53.3% |

The sensitivity independently repeats selection/refitting without matching titles, changing targets and potentially cohorts. It is not a causal contrast.

## Error groups

Groups can overlap. Low-history groups are small and their metrics are unstable. Historical high spending is defined from features, not future outcomes.

| Date | Days | Group | Accounts | RMSE | WAPE |
|---|---:|---|---:|---:|---:|
| 2022-01-01 | 90 | All customers | 4,991 | $528.42 | 58.9% |
| 2022-01-01 | 90 | Low history (<90 days) | 35 | $211.42 | 103.8% |
| 2022-01-01 | 90 | Inactive (>=180 days) | 317 | $112.02 | 183.9% |
| 2022-01-01 | 90 | High historical spending (top 10%) | 500 | $1,207.35 | 46.6% |
| 2022-05-01 | 90 | All customers | 5,004 | $553.41 | 51.4% |
| 2022-05-01 | 90 | Low history (<90 days) | 6 | $214.32 | 130.6% |
| 2022-05-01 | 90 | Inactive (>=180 days) | 311 | $248.15 | 180.7% |
| 2022-05-01 | 90 | High historical spending (top 10%) | 501 | $1,203.08 | 38.4% |
| 2022-01-01 | 180 | All customers | 4,991 | $886.97 | 55.0% |
| 2022-01-01 | 180 | Low history (<90 days) | 35 | $405.32 | 107.8% |
| 2022-01-01 | 180 | Inactive (>=180 days) | 317 | $261.99 | 149.3% |
| 2022-01-01 | 180 | High historical spending (top 10%) | 500 | $1,961.20 | 43.2% |
| 2022-05-01 | 180 | All customers | 5,004 | $869.90 | 46.3% |
| 2022-05-01 | 180 | Low history (<90 days) | 6 | $877.23 | 112.0% |
| 2022-05-01 | 180 | Inactive (>=180 days) | 311 | $382.52 | 126.4% |
| 2022-05-01 | 180 | High historical spending (top 10%) | 501 | $1,899.01 | 35.9% |

## Examples for an interview

Examples are selected by forecast percentile, not by observed outcome. They are descriptive, not success-case cherry-picks.

| Example | Days | Account | Predicted | Actual | Recency | History |
|---|---:|---|---:|---:|---:|---:|
| Low forecast | 90 | R_emksH6nlvPWgMA9 | $26.47 | $26.91 | 212 | 1289 |
| Median forecast | 90 | R_3MGNtEcAhhmZgxr | $397.02 | $113.95 | 1 | 1443 |
| High forecast | 90 | R_3MhBAq6V6XHU9ln | $1,678.02 | $1,558.59 | 1 | 1459 |
| Low forecast | 180 | R_3iyTuoKtVb3y4RA | $28.51 | $539.26 | 115 | 115 |
| Median forecast | 180 | R_08uYA7fb4unHGkF | $882.08 | $2,121.76 | 18 | 956 |
| High forecast | 180 | R_SGAAoUST7I3bMpr | $3,838.52 | $1,940.58 | 11 | 1069 |

## Interview interpretation

State both error and ranking results, then acknowledge that ranking gain may be small or negative even when RMSE improves. Discuss normalized errors instead of choosing a horizon by its dollar RMSE. Inspect calibration and conditional uncertainty before recommending a horizon. Do not tune models using these final test outcomes.
