# model_05_position_projection

Current physical package for Layer 5 `PositionProjectionModel` deterministic scaffold.

Owns local mapping from final adjusted `alpha_confidence_vector` plus point-in-time current/pending position, friction, portfolio, risk-budget, and policy context into `position_projection_vector`. The scaffold implements:

- alpha-to-position prior conversion;
- pending-adjusted effective exposure;
- signed target exposure and target-current gap projection;
- gap-aware cost-to-adjust scoring;
- risk-budget compression and horizon resolution;
- offline position-utility labels and leakage assertions in `evaluation.py`.

Boundary: this package projects target position state only. It must not emit buy/sell/hold/open/close/reverse, instrument choice, option-contract fields, order routing, or broker mutation fields.
