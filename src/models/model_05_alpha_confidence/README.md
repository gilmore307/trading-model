# model_05_alpha_confidence

Physical package for Layer 5 `AlphaConfidenceModel` deterministic scaffold.

Owns local conversion from reviewed Layer 1/2/3 state plus Layer 4 `event_failure_risk_vector` into the final adjusted `alpha_confidence_vector`. The scaffold keeps `base_alpha_vector` as diagnostics only and implements:

Layer 5 trains on dense minute-level target-state rows from the accepted Layer 3 target universe. Candidate-routing thresholds decide which scored rows proceed downstream; they are not training pre-filters.

- base state alpha encoding;
- baseline-adjusted alpha diagnostics;
- Layer 4 event-failure conditioning diagnostics;
- path-risk and confidence/reliability calibration;
- offline alpha outcome labels and leakage assertions in `evaluation.py`.

Boundary: this package must not output position size, target exposure, buy/sell/hold, option selection, broker execution, or future outcome fields in inference rows.
