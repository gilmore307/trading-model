# Layer 6 Dynamic Risk Policy

Status: active architecture revision. Layer 6 uses the physical implementation surface src/models/model_06_dynamic_risk_policy/.

## Purpose

DynamicRiskPolicyModel converts whole-market state, systemic event pressure, alpha quality, and replayed portfolio/account capacity into dynamic_risk_policy_state.

It is a model-internal policy state, not an execution hard-limit gate. Hard order boundaries, account kill switches, and broker permission remain execution/order-gate responsibilities.

## Inputs

- Layer 1 market_context_state
- broad/systemic event-risk state
- Layer 5 alpha_confidence_vector
- replayed portfolio exposure state
- replayed account capacity state

The layer is primarily global-market driven. Sector or target-specific evidence can cap, skip, or haircut the current target, but must not define the global risk budget.

## Outputs

- dynamic_risk_policy_state_ref
- dynamic_risk_policy_state
- dynamic_risk_policy_diagnostics
- 6_* dynamic risk-budget, premium-budget, exposure-permission, haircut, capacity, stability, and confidence score families

## Boundary

Layer 6 does not emit buy/sell/hold, order size, broker route, option contract, account mutation, or hard-limit overrides. Downstream Layer 7 consumes the state when projecting target position state.
