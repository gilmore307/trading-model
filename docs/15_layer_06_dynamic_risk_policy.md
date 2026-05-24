# Layer 6 Dynamic Risk Policy

Status: accepted Layer 6 design route; deterministic V1 scaffold implemented in `src/models/model_06_dynamic_risk_policy/`.

## Purpose

DynamicRiskPolicyModel converts minute-level whole-market state, systemic event pressure, and replayed portfolio/account capacity into dynamic_risk_policy_state. Alpha quality is an optional conditioning input when the row is tied to a candidate or active position.

It is a model-internal policy state, not an execution hard-limit gate. Hard order boundaries, account kill switches, and broker permission remain execution/order-gate responsibilities.

## Inputs

- Layer 1 market_context_state
- broad/systemic event-risk state
- Layer 5 alpha_confidence_vector when the row is candidate- or position-conditioned
- replayed portfolio exposure state
- replayed account capacity state

The layer is primarily global-market driven. Sector or target-specific evidence can cap, skip, or haircut the current target, but must not define the global risk budget.

## Training Sample Granularity

Layer 6 training must use minute-level continuous risk-policy rows. Live runtime components may trigger Layer 6 on demand, but training should still include every eligible market minute so the model learns the risk-policy state during both action and no-action periods.

Layer 6 has three accepted row scopes:

- `global`: one portfolio/account policy row per eligible minute, independent of any specific target candidate.
- `target_candidate`: a candidate-conditioned policy row when Layer 5 has produced an alpha candidate for the minute.
- `active_position`: a position-conditioned policy row when an existing position needs minute-level add/reduce/hold context for Layer 7.

The base training table is not `minute x all symbols`. It is a minute-level global policy table plus target/position-conditioned rows where a candidate or active position exists. This keeps Layer 6 trained on every minute of risk context without pretending every symbol has a budget decision every minute.

The `global` row learns the background budget posture: risk-on/risk-off, premium budget pressure, market stress haircut, systemic event haircut, portfolio capacity, policy stability, and policy confidence. Candidate and active-position rows inherit that context and add Layer 5 alpha quality or position context for downstream Layer 7.

## Calendar-event pressure

Layer 6 does not own raw trading-calendar event interpretation. Overnight/weekend/holiday closures, early closes, triple-witching, index rebalances, Nasdaq-100 rebalance, and similar scheduled market-structure dates are Layer 4 event-risk families when reviewed evidence shows that the date changes liquidity, forced flow, de-risking, gap behavior, or path risk.

Layer 6 consumes the accepted Layer 4 / Layer 5 pressure from those events. For example, a high `4_event_session_gap_risk_score_<horizon>` or a lowered Layer 5 alpha-tradability/path-quality score can reduce Layer 6 risk budget, premium budget, or new-exposure permission. Layer 6 must not independently infer raw calendar-event risk from the date alone.

## Outputs

- dynamic_risk_policy_state_ref
- policy_scope
- policy_scope_id
- dynamic_risk_policy_state
- dynamic_risk_policy_diagnostics
- 6_* dynamic risk-budget, premium-budget, exposure-permission, haircut, capacity, stability, and confidence score families

## Boundary

Layer 6 does not emit buy/sell/hold, order size, broker route, option contract, account mutation, or hard-limit overrides. Downstream Layer 7 consumes the state when projecting target position state.
