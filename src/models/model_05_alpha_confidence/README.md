# model_05_alpha_confidence

Physical package for Layer 5 `AlphaConfidenceModel`.

Primary score semantics: `5_alpha_confidence_score_<horizon>` is the normalized after-cost alpha score when a trained Layer 5 artifact is supplied. `0.5` is after-cost neutral, values above `0.5` are positive expected after-cost edge, and values below `0.5` are negative expected after-cost edge.

Owns local conversion from reviewed Layer 1/2/3 state plus Layer 4 `event_failure_risk_vector` into the final adjusted `alpha_confidence_vector`. Generation requires trained LightGBM GBDT after-cost score artifacts from `training.py`; missing artifacts block generation. It implements:

Layer 5 trains on dense minute-level target-state rows from the accepted Layer 3 target universe. Candidate-routing thresholds decide which scored rows proceed downstream; they are not training pre-filters.

- point-in-time feature assembly for trained Layer 5 artifacts;
- direct normalized after-cost alpha score inference with `lightgbm_gbdt_after_cost_alpha`;
- companion direction, strength, reliability, path-risk, and tradability fields derived from the trained score;
- offline alpha outcome labels and leakage assertions in `evaluation.py`.
- diagnostic event-conditioned alpha contrast in `event_conditioned_contrast.py`, which compares a no-Layer-4 baseline against frozen Layer 4 event-conditioning features and is explicitly not promotion evidence.

Boundary: this package must not output position size, target exposure, buy/sell/hold, option selection, broker execution, or future outcome fields in inference rows.
