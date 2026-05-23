# Layer 6 Dynamic Risk Policy

Status: accepted Layer 6 design route; deterministic V1 scaffold implemented in `src/models/model_06_dynamic_risk_policy/`.

## Purpose

DynamicRiskPolicyModel converts whole-market state, systemic event pressure, alpha quality, and replayed portfolio/account capacity into dynamic_risk_policy_state.

It is a model-internal policy state, not an execution hard-limit gate. Hard order boundaries, account kill switches, and broker permission remain execution/order-gate responsibilities.

## Inputs

- Layer 1 market_context_state
- broad/systemic event-risk state
- Layer 5 alpha_confidence_vector
- point-in-time trading-calendar/session-closure exposure
- replayed portfolio exposure state
- replayed account capacity state

The layer is primarily global-market driven. Sector or target-specific evidence can cap, skip, or haircut the current target, but must not define the global risk budget.

## Trading-calendar risk

Layer 6 owns the base risk from predictable non-trading intervals. This is not a raw-news event and not a standalone alpha source. It is a deterministic market-structure exposure: the longer the market is closed while exposure is held or initiated near the close, the larger the gap/overnight uncertainty budget should be.

The core relationship is monotonic unless later evaluation proves a narrower exception:

```text
intraday / same-session hold < ordinary overnight < weekend < market holiday / long weekend < major long holiday closure
```

Examples:

- ordinary overnight gap risk is smaller than weekend gap risk;
- weekend gap risk is smaller than Thanksgiving, Christmas, or other long-closure risk;
- early closes and holiday-adjacent thin-liquidity sessions may add pre-closure risk even before the closed interval begins.

Layer 6 should represent this as point-in-time calendar/session exposure, for example:

```text
next_market_open_time
non_trading_interval_minutes
closure_type
closure_length_bucket
holiday_name
early_close_flag
pre_holiday_session_flag
calendar_gap_risk_score
calendar_liquidity_thinning_score
```

This base calendar risk can reduce risk budget, premium budget, exposure permission, or increase haircut/review pressure before Layer 7 projects a position. It must not emit orders or hard execution limits.

Layer 4 handles only **event-amplified** session-gap risk. For example, an accepted earnings, macro, geopolitical, or issuer-specific event that overlaps a weekend or holiday closure may raise `4_event_session_gap_risk_score_<horizon>`. The predictable closure risk itself remains Layer 6.

Layer 10 can later test whether specific closure classes repeatedly explain model/strategy failures. If a holiday/weekend/event interaction shows stable incremental failure attribution, Layer 10 may produce a supervision packet for future Layer 4 event-amplified session-gap conditioning.

## Outputs

- dynamic_risk_policy_state_ref
- dynamic_risk_policy_state
- dynamic_risk_policy_diagnostics
- 6_* dynamic risk-budget, premium-budget, exposure-permission, haircut, capacity, stability, and confidence score families

## Boundary

Layer 6 does not emit buy/sell/hold, order size, broker route, option contract, account mutation, or hard-limit overrides. Downstream Layer 7 consumes the state when projecting target position state.
