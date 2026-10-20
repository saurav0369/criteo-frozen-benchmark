# Cycle 021 — G0 strong-baseline audit, real-data results

**Decision: KILL the proposal to introduce a new delayed-feedback architecture on this evidence.** The parent program FRONTIER-EFF-001 remains G0 HOLD. This is a negative/adequacy result, not a novelty claim.

## Execution and provenance
- [Locked protocol committed **before** run](../C021_PRE_REGISTRATION.md): HBASE-009-v0.1.
- [Successful CPU workflow](https://github.com/saurav0369/criteo-frozen-benchmark/actions/runs/39433340247), GitHub Actions run #39433340247. All steps passed, including synthetic no-lookahead controls, official source SHA-256, frozen code hash, results upload, and raw data cleanup.
- [Original full metrics artifact (GitHub; expires per retention policy)](https://github.com/saurav0369/criteo-frozen-benchmark/actions/runs/39433340247/artifacts/12269426970).
- Canonical full metrics file `c021_development_metrics.json` SHA-256: `71b8341531fced23a167b5d3a4712e07b61b19252cbaaeaa5bdf48b248d4e17c` (22,635 bytes). Includes all seven 2-day blocks and paired bootstrap resamples.
- **Source:** 16,468,027 real Criteo impression records, official source SHA-256 `94ac7a465564349bc7ba008602211d5990a3c53cc133abc0aadef61ea2391a98`.
- **Development scoring:** 659,718 predictions, 20,772 positive seven-day conversions (3.149%); `frozen_parity_pass=true`; original C018 prediction digest reproduced exactly `b07ceeaffa7fdf9a633e8afda281580b68e7e47ba99c7d9f7f18a089f1adfc37`. **Holdout outcomes evaluated: zero.**

## Development metrics (lower is better)

| Method | Seven-day log loss | Brier |
| --- | ---: | ---: |
| SGD full context, fully matured | **0.114705159** | **0.027789289** |
| SGD full context, event feedback | 0.115413596 | 0.027907093 |
| FTRL full context, event feedback | 0.118276901 | 0.028063967 |
| Frozen C018 hashed logistic, fully matured | 0.118491600 | 0.028526077 |
| Frozen C018 hashed logistic, event feedback | 0.118492401 | 0.028473254 |
| FTRL full context, fully matured | 0.119755959 | 0.028263554 |

Frozen other simpler baselines and all 12 methods are preserved in the full artifact.

## Adversarial interpretation
- Matured full-context SGD improves log loss over frozen C018 best by **3.20%** relative (0.118491600 → 0.114705159), below 10% screen. It wins all 7 chronological development blocks against frozen matured logistic. **This is an established model with more input features, not evidence for a new mechanism.**
- For otherwise-matched **SGD full-context**, early feedback is **0.61% worse** than matured in log loss (0.115413596 vs 0.114705159); it wins only 2/7 blocks. The 7-block exploratory bootstrap difference early-minus-mature is [0.0001824, 0.0012377].
- For otherwise-matched **FTRL full-context**, early feedback is **1.24% better** than matured (0.118276901 vs 0.119755959), winning 6/7 chronological blocks. Exploratory bootstrap early-minus-mature interval [-0.0023100, -0.0005877]. Yet even the better FTRL model trails the best matured SGD model, so no convincing broadly useful feedback advantage was established.
- The published traditional baselines FTRL-Proximal (McMahan et al., KDD 2013), delayed-feedback modeling (Chapelle, KDD 2014), and ES-DFM (Yang et al., AAAI 2021) show the conceptual problem is heavily researched; **this run does not reproduce Chapelle or ES-DFM**.
- Only 7 nonoverlapping 2-day blocks are available. The percentile bootstrap confidence intervals are exploratory and may not account for user/campaign clustering; they are not confirmatory p-values.
- Event timestamps are proxies, not independently verified data-delivery times. The full-context comparison adds seven categorical features over C018, making attribution of a gain to feature availability rather than optimizer important.
- No evidence meets the >=10% algorithmic screening rule. No heldout model comparison was attempted.

## Next permitted action
**STOP new-model invention on this dataset.** Maintain validated code and evidence. A separate, newly chartered task may audit realistic decision/compute costs or another dataset only if a specific residual bottleneck is identified. Do not endlessly retune this same month of data.

**Gate:** exploratory E3, G0 HOLD for the parent research agenda. HBASE-009 as a purported path to high-end architectural innovation is **KILL** under the 10% screening rule. No foundational or SOTA claims.
