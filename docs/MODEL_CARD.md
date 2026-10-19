# Model card

**Version:** 1.0.0, source-specific run version in `runs/main/manifest.json`.

**Purpose:** Estimate recorded customer purchase value over 90 and 180 days and support historical customer-value coverage under a uniform contact budget. Intended users: portfolio reviewers and analysts studying existing-account spending. Historical demonstration only.

**Data:** Open e-commerce 1.0, Harvard Dataverse DOI 10.7910/DVN/YGLYDY, v1.0, CC0 1.0. Consent-selected U.S. participants, about 5,000 accounts. Exact source identity and exclusion counts appear in the run audit. Valid transaction window: 2018-01-01 through 2022-10-31. Primary retains gift cards, independent sensitivity excludes documented title matches. Identical item rows remain.

**Targets:** Integer-cent item value aggregated to dollar spending over [scoring_date, scoring_date+horizon). Eligible accounts require a prior valid purchase. Fully observed no-purchase outcomes are zero. Incomplete targets are unavailable. The target excludes profit, causal response, returns adjustments unavailable in the source, and spending outside recorded histories.

**Inputs:** Purchase-derived numeric RFM-style behavior, observed history length, 30/90/180/365-day windows, diversity, trailing category shares, trends, month seasonality. Frequency counts purchase days. Identifiers, geography, and late survey responses are excluded from predictive inputs.

**Training and selection:** Monthly snapshots start January 2019. Development scoring dates 2019-2020. Validation January/July 2021, with training-label ends strictly before each fold. Fixed vocabulary from 2018. StandardScaler fits only inside Ridge training. Candidates: scaled trailing-90/365 baselines, Ridge alpha .1/1/10/100, HGB learning rate .05/.1 and max leaves 15/31, 300 iterations, no internal early stopping, seed 42. Select by equal-fold mean RMSE, a 1% band, top-20% capture, then simplicity. ML must improve best baseline RMSE. Select 90 first, then evaluate 180 candidates using max(raw180,selected90).

**Final models:** Fit on labels ending before 2022-01-01 after choices freeze. Same bundle scores 2022-01-01 and 2022-05-01. May features can use purchases before May. No 2022 labels enter fitting. Predictions clamp below zero; 180-day predictions are at least 90-day predictions. Actual selected candidates and measured results appear in RESULTS.md and frozen_selection.json.

**Evaluation:** MAE, RMSE, WAPE, RMSE/mean actual, total calibration, predicted deciles, top-10/20% capture, baseline comparisons, group errors, gift sensitivity, and 500 customer-cluster bootstrap resamples. Intervals are percentile 95% intervals conditional on fitted models. Both dates repeat accounts and some forecast windows overlap. Pooled-date sums can count a purchase more than once and cannot be called unique annual spending.

**Explanation:** Permutation tables measure predictive associations after model choices freeze, using January 2022 and the raw horizon model before cross-horizon adjustment. They do not establish causal drivers. A selected baseline has a single spending input and no learned feature-importance claim.

**Limitations:** Selection/survivorship bias, shared accounts, left-truncated history, assumed common export coverage, temporal regime changes, heavy tails, small independent customer sample, imperfect title-based gift flag, and no marketing treatment or margins. Monetary value on Amazon is not Amazon net revenue/profit. Rankings do not identify who would respond to marketing. No claim of production readiness or prospective accuracy.

**Operations:** Batch scoring is deliberately limited to historical dates in the observed dataset. Load only trusted joblib bundles. A future production release would need new data access and coverage contracts, prospective evaluation, monitoring, and campaign experimentation. Public hosting, GitHub publication, outreach, and production monitoring are outside this release.
