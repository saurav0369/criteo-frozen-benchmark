# Research status and audit trail

**Scientific gate:** G0 HOLD. No real-data metrics have been verified as of this note (2026-10-19 UTC). **No breakthrough or superiority claim is warranted.**

## Provenance
- Official Criteo source: https://huggingface.co/datasets/criteo/criteo-attribution-dataset
- Exact official gzip source size: 653015824 bytes.
- Official published SHA-256: `94ac7a465564349bc7ba008602211d5990a3c53cc133abc0aadef61ea2391a98`.
- Frozen Cycle 018 runner: [c018_runner.py](c018_runner.py). Git blob SHA-1: `566f4c874c8bcd5a8b44e218ba897d0f74585182`. Locally verified identical to the archived Cycle 018 runner.
- Frozen runner SHA-256: `9cdd97e532428ec85c43b409d11eb7db689ff08147978a071edd7a30033b64ba`.
- Local frozen synthetic integrity check: 57/57 assertions, including holdout-poison invariance. These results **are not** Criteo model performance.
- Frozen experimental setup uses 7-day horizon, chronological 30% warmup/40% development/30% reserved holdout by time, deterministic every-10th-row sampling before holdout, 8 predefined methods. No holdout labels are scored.

## Runs
- [Run #1](https://github.com/saurav0369/criteo-frozen-benchmark/actions/runs/39315238423): initial infrastructure proof; **NOT protocol-equivalent** to the original frozen runner.
- [Run #2](https://github.com/saurav0369/criteo-frozen-benchmark/actions/runs/39316627014): exact frozen `c018_runner.py` with full-source size and SHA-256 verification; queued behind Run #1 at this writing.

## Important scientific limitations
- Actual impression and conversion timestamps are observed *event times*, not independently verified historical **arrival/publication times**. Do not claim fully authenticated point-in-time availability.
- Conversions may occur after a 7-day label horizon. The seven-day target is defined separately from the original 30-day dataset conversion label.
- Preselected baselines are not necessarily the strongest published delayed-conversion methods. A G0 development result is a comparison among eight predeclared simple models, **not** a SOTA proof.
- No model run or status may be interpreted as evidence until real-data metrics, source verification, leakage checks and enough independent baselines pass their respective gates.
