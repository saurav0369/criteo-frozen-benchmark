# Cycle 021 — FROZEN G0 exploratory baseline-capacity audit

**Research program:** FRONTIER-EFF-001. **Hypothesis:** HBASE-009-v0.1. **Gate:** G0 HOLD (benchmark-first exploratory pilot, not G1). **Lock timestamp:** 2026-10-20 UTC, before any C021 real-data run. **No new architecture proposed.**

## Motivation and source
C020's checksum-verified Criteo results yielded a near-tie between original 3-feature hashed logistic event and mature models (0.118492401 vs 0.118491600 development log loss). The official Criteo source documents nine impression-context categorical fields (cat1–cat9) plus campaign; C018's strongest baseline used only cat1, cat2 and campaign. This could make the benchmark artificially weak. This is a **baseline adequacy** test.

## Predeclared design
- **Source:** exact verified official `criteo_attribution_dataset.tsv.gz` of 653015824 bytes, SHA256 `94ac7a465564349bc7ba008602211d5990a3c53cc133abc0aadef61ea2391a98`.
- **Source license:** CC BY-NC-SA 4.0, research-only. No raw data uploaded.
- **Target:** conversion within seven days, per C018 frozen `released`. True positives become available at conversion event time *as a proxy*, negatives mature at impression+7d.
- **Split:** time: earliest 30% warmup / next 40% development / last 30% reserved holdout. Observe holdout timestamps for boundary calculation, never read holdout labels or features. Use original deterministic every-10th-row sampling, no random model selection.
- **Baseline:** import **unchanged** `c018_runner.py`, reproduce original eight predictions and exact original prediction digest `b07ceeaffa7fdf9a633e8afda281580b68e7e47ba99c7d9f7f18a089f1adfc37`, require n=659718 and frozen metrics within 1e-9.
- **Four additional strong conventional controls:** online hashed logistic SGD (same .05 learning step as C018), and sparse FTRL-Proximal (alpha=.1,beta=1,l1=1e-6,l2=1); each trained in two otherwise identical versions, one using early event-proxy feedback and one using fully matured feedback.
- **Feature set:** impression-time `campaign` and `cat1`–`cat9` only, 2^18 deterministic stable BLAKE2b buckets, log-odds prior logit(0.005), only available feedback used to update. Sparse FTRL includes bias index; no hyperparameter tuning after development outcomes.
- **Primary metric:** chronological prequential seven-day conversion log loss on development only; secondary Brier and per-2-day chronological block paired differences. Report 10,000 block-bootstrap replications seeded 20261020, acknowledging only ~7 blocks and weak independence.
- **Integrity tests:** positive-label update direction, input-column restriction, holdout-outcome poisoning invariance, exact frozen-reference prediction digest parity. Source checksum required.
- **Thresholds / interpretation:** If a conventional full-context comparator outperforms the best frozen C018 by >=10% relative log loss, conclude the previous benchmark was inadequate and **do not infer new architectural advantage**. If event vs mature difference is <1% in the full-context same-optimizer comparisons, delayed-feedback residual mechanism is unsupported in this setting. An apparent >=10% effect *across 4/6 or more blocks* permits only a specialist-method follow-up, not a breakthrough claim. If ambiguous, HOLD.
- **Boundary:** 30-day observational stream; event timestamps not verified release times; same users may contribute repeated impressions; extra features confound capacity compared with frozen comparator; not a reproduction of Chapelle (KDD 2014) or ES-DFM (AAAI 2021), and FTRL is existing work (McMahan et al. KDD 2013).

**Source references:**
- https://huggingface.co/datasets/criteo/criteo-attribution-dataset
- https://research.google/pubs/ad-click-prediction-a-view-from-the-trenches/
- https://doi.org/10.1145/2623330.2623634
- https://doi.org/10.1609/aaai.v35i5.16587

**Status before running:** LOCKED exploratory pilot, G0 HOLD. Run #3 and source artifact remain unchanged.
