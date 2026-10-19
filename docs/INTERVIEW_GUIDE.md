# Technical interview guide

Read this alongside `WORK_LOG.md` and the generated `docs/RESULTS.md`. The work log explains what happened. This guide explains why the implementation is defensible. Use measured numbers from RESULTS when answering, including a baseline winning if that occurs.

## A 60-second explanation

“I built a reproducible customer-spending forecasting project from real, consented Amazon purchase histories covering about 5,000 accounts. At each historical scoring date I predicted spending over the next 90 and 180 days using only earlier purchases. I compared scaled historical-spend baselines, Ridge regression, and histogram gradient boosting. I used chronological validation with a gap determined by each label's horizon, then froze the fitted models before evaluating two dates in 2022. I evaluated both dollar errors and whether the ranking captured future spending. A Streamlit dashboard shows how a uniform contact budget changes the selected audience. That is value coverage, not incremental campaign return.”

Follow with the selected models, measured test RMSE, WAPE, top-20% capture, and one limitation from RESULTS. Avoid memorizing numbers without their date, units, horizon, and comparison.

## The problem and unit of analysis

**What exactly are you predicting?** A finite sum of recorded purchase value: unit price times quantity over the next 90 or 180 calendar days. This is a regression problem with a nonnegative, skewed monetary target. It does not predict lifetime spending, profit, or the causal effect of an offer.

**What is one example?** One account at one scoring date, with one target for each horizon. A transaction row is an item record, not a reliably identified order. The same account can appear at many dates because the intended use is rescoring existing customers. This creates dependence between observations.

**Why two horizons?** A short contact cycle may favor 90 days, while a planning team may need 180 days. A longer horizon mechanically contains more spending and often larger dollar errors. Compare normalized errors, calibration, stability, and ranking utility. Smaller absolute RMSE at 90 days cannot prove it is better.

**Why this dataset?** It has real longitudinal behavior, account IDs, purchase dates, unit prices, and quantities. A verified original-file checksum and published research provenance make the exercise auditable. It contains roughly 5,000 accounts, even though it has 1.85 million item rows. Those are very different sample sizes.

## Provenance and cleaning

The original is Open e-commerce 1.0, Berke et al., Harvard Dataverse DOI `10.7910/DVN/YGLYDY`, version 1.0, CC0 1.0. The local file came from a mirror and matches the original's MD5. SHA256 also identifies the exact input for this run. A checksum confirms byte identity, not statistical truth or correct dates.

The source includes records beyond the intended analysis window. A single observed latest date would be a bad estimate of complete coverage. The project uses the common 2018-01-01 through 2022-10-31 window, consistent with the source authors' comparable longitudinal analysis. It separately counts later records, including the isolated 2024 anomaly.

**Money:** Parse prices as Decimal and round unit prices to cents using half-up rounding. Multiply integer unit cents by positive integer quantities. Integer aggregation avoids binary floating-point artifacts in accounting totals. Dollar-valued model inputs and targets divide those totals by 100. This doesn't eliminate regression prediction decimals, which need not be whole cents.

**Invalid data:** Reject missing account identifiers, invalid dates, invalid/nonpositive prices, and invalid/nonpositive/fractional quantities. Sequential exclusion counts reconcile exactly to the retained row count. Upper bounds protect integer arithmetic from malformed values. Missing titles, categories, products, and states receive an explicit UNKNOWN value. State and product identifiers normalize to uppercase. Only purchase-derived numerical features enter models.

**Identical rows:** Keep them. Without an order ID, identical customer/date/product/value rows could be legitimate purchases. Deleting them would silently change the target without evidence. The audit reports how many identical rows remain.

**Gift cards:** Primary analysis retains them. Sensitivity excludes titles matching a documented case-insensitive rule: `gift\s+card|gift\s+code|digital\s+code|amazon\s+reload`. This follows the paper's title-based categories. The rule is imperfect: generic digital codes may include other goods, and absent titles may miss cards. Gift cards may overlap economically with later merchandise spending. The sensitivity independently repeats model selection and fitting, so changes combine target/cohort changes and model changes. It is a robustness analysis, not a controlled estimate of gift cards' causal effect.

## Temporal construction: the most important interview topic

Let `s` be the scoring date, `h` a horizon in calendar days, and `E` the exclusive observation end.

Eligibility: account has at least one valid transaction with date `< s`.

Features: functions only of transactions with dates `< s`.

Target: `y(account,s,h) = sum(value for s <= date < s+h)` if `s+h <= E`. Otherwise the target is unavailable (NaN).

Example: scoring on 2022-01-01 makes a purchase on 2021-12-31 historical and a purchase on 2022-01-01 part of the target. The 90-day window ends at 2022-04-01 exclusively. The 180-day window ends at 2022-06-30 exclusively. These are day counts, not three/six calendar months.

**Why retain zeros?** The eligible cohort must be established from history. Filtering to customers with a later purchase would use future knowledge, omit inactivity, and inflate apparent future value. No purchase in a fully observed window gives a recorded zero. No complete observation window gives NaN, not zero. The absence of a transaction cannot establish zero without an observation contract.

**Why monthly snapshots?** They supply different recency, spending patterns, and seasonal contexts without pretending transactions are independent training customers. More snapshots increase training rows, but do not create more independent people. Forecast windows overlap and require careful validation and uncertainty handling.

**Why chronological rather than random splitting?** A random snapshot split can put later behavior of the same customer in training and earlier behavior in validation. It also mixes historical regimes and can train on target periods that would still be in the future at the validation date. That estimates an easier, unrealistic task.

**Why purge labels rather than just features?** A snapshot from December with a 180-day target contains outcomes through the following June. Its features may be historical, but its label would not exist at a January scoring date. Every validation training example therefore satisfies `label_end < validation_date`. The strict inequality is deliberately conservative: it omits boundary examples even when an exclusive endpoint exactly at the cutoff could be considered known.

**Validation:** January 1 and July 1, 2021. Candidate training scoring dates remain in 2019-2020 and labels must mature before the corresponding fold. Equal weighting of the two fold RMSEs keeps the selection rule explicit.

**Final fitting:** After validation choices freeze, use all monthly examples with labels ending before January 1, 2022. This can include matured 2021 validation-period labels, which is standard refitting after selection. It cannot include any 2022 outcome. The final models stay fixed for both January and May tests. May features may use the observed history through April, including events that were outcomes for January. That is legitimate information available by May, and differs from retraining on test labels.

**“Are the tests independent?”** No. The same customers recur, January's 180-day window overlaps May outcomes, and 90-day windows nest inside 180-day windows. The report explicitly states this. The customer-level bootstrap preserves each customer's repeated test rows. Generalization to a new calendar regime remains uncertain with only two test dates.

## Features and preprocessing

Recency is days since the last purchase. History length is days since the first observed purchase, not true account tenure. Lifetime features use history since January 2018. For 30/90/180/365-day lookbacks, measure spending, total quantity, distinct purchase days, distinct product IDs, category diversity, spending per purchase day, and available history days.

**Why purchase days?** No order ID exists. Calling distinct rows or dates “orders” would invent an unavailable measurement. Multiple purchases on the same day count once for the frequency feature but all values and quantities still sum.

**Why history length and observed days?** A new account with $50 over 30 observed days differs from an account with $50 over a whole observed year. The observation starts in 2018, so even old accounts' history is left truncated. Trailing-spend baselines use the specified fixed scaling and can underpredict short-history customers. Group error tables make that weakness visible.

Category spending shares describe the mix of trailing-year spending. The vocabulary consists of the top 12 categories by 2018 value, plus UNKNOWN and OTHER. It is frozen before all snapshots. New categories map to OTHER. This sacrifices adaptation to avoid later category popularity influencing earlier features. A production system could fit a versioned mapping inside each training cycle instead.

Spending trends compare recent spending with a preceding interval, accounting for unequal interval lengths where needed. Month sine/cosine features encode annual periodicity without pretending December and January are far apart. Purchase-only features exclude identifiers and late-collected survey answers. Account ID remains an export/join key only.

StandardScaler fits inside each Ridge training pipeline. It never sees validation rows when estimating means and scales. HGB uses numeric features without requiring standardization. All feature code is shared by training and batch scoring to prevent training/serving skew.

## Models and selection

**Baselines:** `spend_90 * h/90` and `spend_365 * h/365`. They assume recent spending rates persist. They are cheap, interpretable, and often strong. A good ML project compares against them and retains them if they win.

**Ridge:** Minimize squared residuals plus `alpha * sum(coefficients squared)`, with standardized features. It shrinks unstable coefficients and handles correlated spending windows better than unregularized regression. Alphas are 0.1, 1, 10, 100. Coefficients describe conditional predictive associations, not causal effects.

**Histogram gradient boosting:** Sequential trees learn residual patterns and nonlinear interactions. Histogram binning reduces split-search cost. The bounded search uses learning rates 0.05/0.1, max leaf nodes 15/31, and 300 boosting iterations. Internal random early stopping is disabled because a random holdout would undermine the explicit temporal validation. The external chronological folds evaluate all candidates. These choices balance capacity against an account sample of about 5,000.

**Why this loss?** Selection optimizes RMSE, so Ridge and squared-error boosting align with large-error sensitivity. This emphasizes high-spending accounts, which is relevant to value coverage but can be sensitive to outliers. Log-target, Tweedie, and hurdle models are reasonable future experiments, not post-test substitutions. A log transform would require bias-aware inverse transformation and would change the error emphasis.

**Selection rule:** Mean fold RMSE first. Among candidates within 1% of the best eligible RMSE, prefer stronger top-20% capture, then lower model complexity. ML must improve the best baseline RMSE to qualify. This is a predeclared practical tie rule, not statistical proof that a 1% difference is meaningful.

**Nonnegative forecasts:** Clamp predictions below zero. Spending labels are nonnegative; unconstrained Ridge can otherwise predict negative dollars. Evaluate the clamp throughout.

**Horizon coherence:** Set `p180 = max(raw_p180, p90)`. Because an actual 180-day sum contains the 90-day window, this preserves a basic consistency constraint. Select 90 first, since its forecasts never change. Then evaluate every 180-day candidate using the selected 90-day forecasts. Use the same adjustment on validation, test, and scoring, and report its frequency. It can change calibration and RMSE, so applying it only in the dashboard would invalidate reported performance.

## Metrics you must explain

| Metric | Formula/meaning | Important limitation |
|---|---|---|
| MAE | mean absolute dollar error | Less sensitive to rare very large misses |
| RMSE | square root of mean squared dollar error | Heavy spenders/outliers can dominate |
| WAPE | sum absolute error / sum actual spending | Undefined if total spending is zero, not average customer percent error |
| Normalized RMSE | RMSE / mean actual spending | Useful across horizon scales, still sensitive to outliers |
| Total ratio | total predicted / total actual | Aggregate calibration can hide offsetting customer errors |
| Top-20% capture | actual dollars in highest-ranked 20% / all actual dollars | Ranking utility, not campaign lift or individual accuracy |
| Capture gain | selected capture minus historical-ranking capture, in percentage points | Depends on cohort, horizon, and selection size |

**Why not MAPE?** Zero targets make individual percentage errors undefined and near-zero targets unstable. WAPE aggregates the denominator instead. This does not make WAPE suitable for comparing populations with radically different spending distributions without context.

**Calibration deciles:** Rank customers by predicted value, split into ten nearly equal groups with deterministic tie handling, then compare mean predicted and actual dollars. The highest decile can dominate overall error. Good ranking and poor calibration can coexist because rankings depend on ordering, not absolute scale.

**Group errors:** Low history means less than 90 observed days. Inactive means at least 180 days since the last purchase. High spending means the top 10% of historical trailing-year spending within the test date. These groups are descriptive and can overlap. They are not causal segments or protected-group fairness tests.

**Bootstrap:** Draw accounts with replacement 500 times. If an account appears at both test dates, include both rows for every draw of that account. Recompute metrics and use the 2.5th/97.5th percentiles. This estimates sampling uncertainty conditional on the fitted models and chosen cohort. It does not refit models, fix selection bias, guarantee coverage in future years, or turn repeated snapshots into independent observations. The combined metric pools account-date observations; totals across overlapping windows can double count calendar purchases and are not unique annual spending.

## Marketing simulator

Capacity is `min(eligible_accounts, floor(budget / uniform_contact_cost))`. A zero budget selects nobody. An oversized budget selects everyone. Negative/nonfinite budgets and nonpositive/nonfinite costs raise errors. Decimal arithmetic avoids a binary-float edge case where $0.30/$0.10 might incorrectly floor below three.

Compare predicted spending ranking to trailing-365-day spending, ascending recency, and a seeded random permutation. Each strategy receives the same capacity. Account-ID sorting breaks ranking ties consistently. Overlap is the fraction of the predicted audience shared by another strategy. At zero capacity overlap is defined as zero.

The spending of selected accounts is **covered spending**. Those customers may have purchased without contact. To estimate incremental return, collect randomized treatment/control assignment, contact/offer costs, response outcomes, and contribution margins. Optimizing incremental profit would then use uplift and cost, not merely highest expected spending. This dataset cannot establish an optimal offer or campaign ROI.

## Software engineering and reproducibility

- `python -m amazon_clv run`: audit, build snapshots, select, fit, test, export, rerun sensitivity, draw charts.
- `python -m amazon_clv score`: load frozen bundle, use the same feature builder and prediction function, export both horizons.
- Model bundle includes feature columns, category map, both fitted models, version, training cutoff, and observation end.
- Source hash, run manifest, frozen selection, split audits, and saved outputs make results traceable. A completed run directory is protected against accidental overwrite.
- Cached dashboard tables use file modification stamps for invalidation. Models use `st.cache_resource`; data use `st.cache_data`. Interaction never starts training.
- Unit tests target temporal and accounting failure modes. A synthetic end-to-end smoke tests wiring. The full real-data run supplies evidence. Clean-kernel notebooks explain outputs without silently changing models.
- A dependency lock pins the tested closure for Python 3.12 on macOS ARM64. Binary wheels/platform support may differ elsewhere. Artifact authoring uses an additional Codex-bundled Node runtime for editable slides; Python analysis and dashboard do not depend on it.
- Large inputs, run artifacts, environments, and model binaries are Git-ignored. Small documentation, code, tests, notebooks, and final report/deck can be published after review. No repository was published in this task.

## Tests to describe concretely

“I wrote a future-invariance test: append a large future purchase and assert every earlier feature remains identical. I tested purchases on the scoring date and right endpoint to protect interval semantics. I tested that a customer with no future purchases remains with zero, while an incomplete future horizon stays NaN. I asserted every training label ends before its fold cutoff. I tested missing/new categories, inactive and short-history accounts, serialized-model equivalence, and the exact customer IDs in budgeted CSV exports.”

Do not merely say “I tested leakage.” Name the specific counterexample and expected behavior.

## Honest limitations and next steps

The sample favors established accounts still active at recruitment, is consent-selected, and is not a representative acquisition cohort. Accounts can be shared and may represent households. The common coverage rule assumes the collected export histories are complete through October 2022, which transaction records alone cannot prove for each account. Survey information is later collected and intentionally excluded. Returns, cancellations, profit margins, true order IDs, campaign assignment, and response are unavailable. Current spending behavior may differ substantially from 2022. Predictive feature importance cannot show what a marketer should change to cause spending.

With more data, add prospective monitoring, a genuinely later untouched test period, account-level coverage metadata, randomized campaign experiments, uncertainty-aware budget decisions, and a temporally validated comparison with alternative target distributions. These are future directions and were not claimed as completed production capabilities.

## Practice prompts

Use the measured January 90-day group errors to practice interpreting scale: high historical spenders have RMSE about $1,207 versus $528 overall, but WAPE is 46.6% versus 58.9% overall. Inactive accounts have RMSE only $112 but WAPE 183.9%, because actual spending is low. Short histories include only 35 accounts, with WAPE 103.8%, so avoid broad conclusions from that small group. These examples show why one error metric and one aggregate average are insufficient.

1. Draw the scoring date and both half-open target windows. Explain a purchase exactly on each boundary.
2. Explain why a December 2020 snapshot may be excluded from January 2021 training despite its historical features.
3. Explain why May 2022 features may include April spending while the model remains frozen.
4. State the measured winning model and explain why a baseline winning is a useful finding.
5. Distinguish RMSE, WAPE, aggregate calibration, and top-20% capture using one customer example.
6. Explain what the clustered bootstrap preserves and what it cannot tell you.
7. Compute an audience size, spending coverage, and overlap by hand for five accounts.
8. Explain what additional data would be needed to claim campaign ROI.
9. Identify one implementation bug a test prevented and one actual setup problem from the work log.
10. Give a five-minute walkthrough of `data.py`, `features.py`, `modeling.py`, and `pipeline.py`, ending with the saved split audit.

## Sources

- Dataset: https://doi.org/10.7910/DVN/YGLYDY
- Data descriptor: https://www.nature.com/articles/s41597-024-03329-6
- Streamlit caching: https://docs.streamlit.io/develop/concepts/architecture/caching
