# model_05_alpha_confidence

Legacy physical package for conceptual Layer 4 `AlphaConfidenceModel` deterministic scaffold.

Owns local conversion from reviewed Layer 1/2/3 state plus Layer 8 event-risk context into the final adjusted `alpha_confidence_vector`. The scaffold keeps `base_alpha_vector` as diagnostics only and implements:

- base state alpha encoding;
- baseline-adjusted alpha diagnostics;
- event adjustment and high-quality event override diagnostics;
- path-risk and confidence/reliability calibration;
- offline alpha outcome labels and leakage assertions in `evaluation.py`.

Boundary: this package must not output position size, target exposure, buy/sell/hold, option selection, broker execution, or future outcome fields in inference rows.
