# model_05_alpha_confidence

Physical package for Layer 5 `AlphaConfidenceModel`.

Primary score semantics: `5_alpha_confidence_score_<horizon>` is the normalized after-cost alpha score when a trained Layer 5 artifact is supplied. `0.5` is after-cost neutral, values above `0.5` are positive expected after-cost edge, and values below `0.5` are negative expected after-cost edge.

Owns local conversion from reviewed Layer 1/2/3 state plus Layer 4 `event_failure_risk_vector` into the final adjusted `alpha_confidence_vector`. The trained path uses `training.py` to build a direct after-cost score artifact. The deterministic scaffold remains a cold-start baseline and keeps `base_alpha_vector` as diagnostics only. It implements:

Layer 5 trains on dense minute-level target-state rows from the accepted Layer 3 target universe. Candidate-routing thresholds decide which scored rows proceed downstream; they are not training pre-filters.

- base state alpha encoding;
- baseline-adjusted alpha diagnostics;
- Layer 4 event-failure conditioning diagnostics;
- path-risk and confidence/reliability calibration;
- trained normalized after-cost alpha score inference when an artifact is provided;
- offline alpha outcome labels and leakage assertions in `evaluation.py`.

Boundary: this package must not output position size, target exposure, buy/sell/hold, option selection, broker execution, or future outcome fields in inference rows.
