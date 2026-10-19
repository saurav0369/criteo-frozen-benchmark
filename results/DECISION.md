# Cycle 020: verified real-data development result and gate decision

**Decision: G0 HOLD.** The freeze-preserving real-data run succeeded but did not establish a novel advantage or G1 advancement.

- Official Criteo gzip verification: 653015824 bytes and SHA-256 `94ac7a465564349bc7ba008602211d5990a3c53cc133abc0aadef61ea2391a98`; both checks passed in GitHub Actions.
- Successful execution: [GitHub Actions Run #3](https://github.com/saurav0369/criteo-frozen-benchmark/actions/runs/39317717290), using the original frozen `c018_runner.py` (Git blob SHA `566f4c874c8bcd5a8b44e218ba897d0f74585182`).
- Original eight-model outcome: [c018_dev_metrics.json](c018_dev_metrics.json). Original downloaded JSON SHA-256: `e11a24b204924f13ba59c5e74d2da4a4d6cdf9d9591b4903304464edac01c0f3`. Preservation of original output data (no metric edits).
- Real-data source rows: 16,468,027; one in ten sampled before holdout; 512,050 warmup samples; **659,718 development predictions**; **zero holdout labels evaluated**.
- Time split: first 30% warmup, next 40% development, last 30% reserved holdout. The time scan reads timestamps across the source to define boundaries, not outcome labels.
- Scientific status field in the original JSON is a built-in guard: `SYNTHETIC_ONLY unless official source externally verified`. The workflow independently performed and passed full official-source size and SHA-256 verification **before** running the program. The unmodified metric artifact retains this literal guard string for provenance.

## Development results (lower is better)

| Predeclared method | Log loss | Brier |
|---|---:|---:|
| fixed_prior | 0.171678493 | 0.031196319 |
| global_event | 0.146550213 | 0.031183424 |
| rolling_event | 0.142064749 | 0.030711829 |
| campaign_event | 0.130461113 | 0.030243755 |
| global_mature | 0.139902115 | 0.030496649 |
| campaign_mature | 0.124109993 | 0.029109450 |
| hashed_logit_event | 0.118492401 | **0.028473254** |
| hashed_logit_mature | **0.118491600** | 0.028526077 |

- Fully matured campaign feedback beats naive early-event campaign feedback by approximately 4.87% log loss, not the 10% screening threshold; this is a comparison between simple existing variants, not a new method.
- Hashed-logit mature versus early log-loss difference is only 0.000000801 (0.000676% relative). The early model has better Brier, and we have **no paired time-block or user-cluster uncertainty** yet. Treat the performance difference as a tie, not evidence of superiority.
- These are development-only metrics; they establish reproducible function of the pipeline, **not** state-of-the-art or production readiness.

## Claim boundary and next research decision

**Claim:** checksum-verified, chronological real-event-time Criteo development evaluation of eight frozen baselines on free GitHub Actions CPU, completed successfully.

**Cannot claim:** a novel architecture, 10% improvement on strongest contextual comparator, independently verified label-publication timing, properly clustered confidence intervals, generalization to another time window, or holdout performance.

**Next permitted action:** independent negative-control audit and a stronger established delayed-conversion baseline, both preregistered before any use of the sealed holdout. If no reproducible 10% effect survives, close the algorithmic candidate. No new speculative architecture or repeated post-hoc tuning.
