# model_06_residual_event_governance

Canonical package boundary for current `M06 Residual Event Governance`.

This model owns missed-event checks, residual event intervention, attribution, and future event-family promotion evidence. It must not become a hindsight alpha/action model or mutate broker/account state.

The current deterministic pilot consumes the M04 `unified_decision_vector_ref` /
`direct_underlying_intent`, an optional M05 `option_expression_plan_ref` /
`option_expression_plan`, and point-in-time event observations. It emits
`event_risk_intervention_ref`, `event_risk_intervention`, and `6_*` residual
event-governance score/resolution fields.

Retired `event_context_vector` / `underlying_action_plan` vocabulary is migration
source only and must not be emitted by this current package.
