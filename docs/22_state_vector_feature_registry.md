# State Vector Feature Semantics Registry

Status: accepted semantics guardrail for the current six-model stack

This file owns semantic guardrails for score families and vector fields used by current model contracts. Exact registry-backed field names must still route through `trading-manager` before cross-repository dependency.

## M01 Background Context

M01 score families should keep these axes separate:

- market direction and direction strength;
- market trend quality and stability;
- volatility/stress/transition risk;
- breadth, dispersion, correlation/crowding;
- sector/industry relative behavior;
- liquidity pressure/support;
- coverage and data quality.

M01 fields must not directly encode target selection, action, option expression, or event-governance intervention.

## M02 Target State

M02 score families should keep these axes separate:

- target tradability and liquidity/cost;
- target path quality, persistence/reversion, and transition risk;
- target/background interaction;
- target eligibility and ranking evidence;
- optionability diagnostics where they summarize target-level state rather than choosing contracts;
- target-state data quality.

Raw ticker/company identity remains audit/routing metadata and must not be a fitted feature.

## M03 Event State

M03 score families should keep these axes separate:

- event presence/proximity and applicability;
- response strength and response direction tendency;
- response uncertainty;
- path risk, gap risk, reversal risk, liquidity disruption, contagion risk;
- entry-block, exposure-cap, disable, and review pressure;
- source/context quality.

M03 consumes accepted event parameters from M06. It must not mutate event-family identity, scope, visibility, selected impact windows, or allowed use.

## M04 Unified Decision

M04 score families should keep these heads separate:

- edge / after-cost alpha;
- risk policy and budget pressure;
- exposure, size, position gap, and regret;
- direct-underlying action type, entry/exit/risk-plan quality, no-trade, maintain, and invalidation profile;
- cost, turnover, fill realism, churn, and path quality diagnostics.

M04 must not choose option contracts or send broker orders.

## M05 Option Expression

M05 score families should keep these axes separate:

- underlying-only versus option expression eligibility;
- long-call and long-put candidate utility;
- spread/liquidity/fill realism;
- DTE, delta/moneyness, IV, vega/theta, gamma/pin risk, and event-surface sensitivity;
- no-option, unavailable, and not-applicable status.

M05 is offline expression guidance, not live execution.

## M06 Residual Event Governance

M06 score families should keep these axes separate:

- residual event presence and attribution confidence;
- event severity, timing proximity, scope, and target relevance;
- residual intervention utility;
- overblock/opportunity cost;
- stale regime/decay state;
- future event-family packet eligibility.

M06 may emit warning/cap/block/review/reduce/flatten-review guidance and future M03 promotion packets, but it must not send orders or mutate accounts.

## Retired Field Prefixes

Old `1_*` through `10_*` physical score prefixes may appear in retained ten-layer implementation packages and historical artifacts. They are migration-source fields and should not define new current contracts.
