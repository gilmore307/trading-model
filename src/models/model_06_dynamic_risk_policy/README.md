# model_06_dynamic_risk_policy

Current physical package for Layer 6 DynamicRiskPolicyModel.

It owns deterministic local conversion from minute-level global market state, systemic event pressure, alpha quality when present, and portfolio/account replay context into dynamic_risk_policy_state. It supports `policy_scope = global`, `target_candidate`, or `active_position` rows. It does not enforce hard order boundaries or authorize broker execution.
