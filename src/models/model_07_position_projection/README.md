# model_07_position_projection

Physical package for Layer 7 `PositionProjectionModel` baseline generator.

Owns local mapping from final adjusted `alpha_confidence_vector` plus point-in-time current/pending position, friction, portfolio, risk-budget, and policy context into `position_projection_vector`. The scaffold implements:

- alpha-to-position prior conversion;
- pending-adjusted effective exposure;
- signed target exposure and target-current gap projection;
- gap-aware cost-to-adjust scoring;
- risk-budget compression and horizon resolution;
- offline position-utility labels and leakage assertions in `evaluation.py`.

Training should use dense minute-level projection-state rows whenever the point-in-time Layer 5/6 and position-context inputs exist. Action triggers and Layer 8 handoff thresholds are downstream routing policies, not training-row admission filters.

Target exposure changes are state projections, not automatic position changes. Layer 7 emits target exposure, position gap, utility, cost, risk-budget fit, stability, confidence, and pending-adjusted exposure evidence only. Layer 8 owns maintain/no-trade/open/increase/reduce/close/cover planning.

Boundary: this package projects target position state only. It must not emit buy/sell/hold/open/close/reverse, instrument choice, option-contract fields, order routing, or broker mutation fields.
