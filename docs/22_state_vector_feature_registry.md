# State Vector Feature Semantics Registry

Status: accepted semantics guardrail for the current five-model stack

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

M01 fields must not directly encode target selection, action, option expression, or event-governance component-control.

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

M03 consumes accepted event parameters from M03 event-governance tooling and reviewed event evidence. It must not mutate event-family identity, scope, visibility, selected impact windows, or allowed use during inference.

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

## M03 Event-Governance Tooling

M03 event-governance tooling evidence should keep these axes separate before it becomes M03 input:

- residual event presence and attribution confidence;
- event severity, timing proximity, scope, and target relevance;
- residual component control utility;
- overblock/opportunity cost;
- stale regime/decay state;
- future event-family packet eligibility.

M03 event-governance tooling may propose future event-family packets and reviewed effect-model evidence. Runtime warning/cap/block/reduce/flatten actions are component-owned and must not be represented as M03 model outputs.

## Retired Field Prefixes

Historical score prefixes may appear in immutable artifacts, but active feature-registry entries must define the current M01-M05 contracts only.
