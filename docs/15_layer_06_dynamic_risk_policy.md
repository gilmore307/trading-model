# Layer 6 Dynamic Risk Policy

Status: accepted Layer 6 design route; deterministic V1 scaffold implemented in `src/models/model_06_dynamic_risk_policy/`.

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

## Calendar-event pressure

Layer 6 does not own raw trading-calendar event interpretation. Overnight/weekend/holiday closures, early closes, triple-witching, index rebalances, Nasdaq-100 rebalance, and similar scheduled market-structure dates are Layer 4 event-risk families when reviewed evidence shows that the date changes liquidity, forced flow, de-risking, gap behavior, or path risk.

Layer 6 consumes the accepted Layer 4 / Layer 5 pressure from those events. For example, a high `4_event_session_gap_risk_score_<horizon>` or a lowered Layer 5 alpha-tradability/path-quality score can reduce Layer 6 risk budget, premium budget, or new-exposure permission. Layer 6 must not independently infer raw calendar-event risk from the date alone.

## Outputs

- dynamic_risk_policy_state_ref
- dynamic_risk_policy_state
- dynamic_risk_policy_diagnostics
- 6_* dynamic risk-budget, premium-budget, exposure-permission, haircut, capacity, stability, and confidence score families

## Boundary

Layer 6 does not emit buy/sell/hold, order size, broker route, option contract, account mutation, or hard-limit overrides. Downstream Layer 7 consumes the state when projecting target position state.
