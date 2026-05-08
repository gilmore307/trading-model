# Layer 8 — OptionExpressionModel

`OptionExpressionModel` consumes the Layer 7 `underlying_action_plan` / `underlying_action_vector` handoff plus point-in-time option-chain context to produce an offline `option_expression_plan` and `expression_vector`.

It is the first layer that may select option expression and contract constraints. It is still not live execution.

## Boundary

Layer 8 owns:

- long-call, long-put, or no-option-expression selection;
- option right, selected contract reference, and contract-fit diagnostics;
- DTE, delta/moneyness, IV, vega/theta, spread/liquidity, fill-quality, and premium-risk constraints;
- side-neutral use of Layer 7 path assumptions: entry price, target/range, stop, holding time, path quality, reversal risk, drawdown risk, and favorable/adverse move estimates;
- offline option-expression labels and promotion evidence.

Layer 8 does **not** own:

- broker order type, route, time-in-force, send/cancel/replace flags, or broker order ids;
- final order quantity, final approval, or account mutation;
- multi-leg spread construction in V1;
- direct-underlying planned action resolution, which belongs to Layer 7;
- real live/paper routing, which remains in `trading-execution`.

## Inputs

Required point-in-time inputs:

```text
available_time
tradeable_time
target_candidate_id
underlying_action_plan_ref
underlying_action_plan
underlying_action_vector / Layer 7 resolved fields
option_contract_candidates
option_expression_policy
```

Useful context inputs:

```text
market_context_state
sector_context_state
target_context_state
event_context_vector
position_projection_vector
current option position / premium risk context
pending option exposure / pending option orders
option quote snapshot references
```

Layer 8 must carry the exact quote/snapshot identity used for replay:

```text
option_chain_snapshot_ref
option_quote_available_time
underlying_quote_snapshot_ref
underlying_reference_price
```

Pending option context should be included to avoid duplicate plans:

```text
pending_option_orders
pending_option_premium_exposure
pending_option_fill_probability_estimate
pending_option_cancellable_state
```

Option candidates must be timestamped contract observations. They may include:

```text
contract_ref
option_right / right
expiration
dte / days_to_expiration
strike
moneyness
delta
gamma
theta
vega
iv / implied_volatility
iv_rank
bid_price / bid
ask_price / ask
mid_price / mid
volume
open_interest
contract_multiplier
exercise_style
settlement_type
is_weekly
is_monthly
is_adjusted_contract
last_trade_time
quote_age_seconds
bid_size
ask_size
spread_abs
spread_pct_mid
intrinsic_value
extrinsic_value
breakeven_price
theoretical_value
```

Future realized option returns, target/stop outcomes, and best-contract hindsight are evaluation labels only and must not be present in inference rows.

## Outputs

Primary output:

```text
option_expression_plan
```

Vector output:

```text
expression_vector
```

Resolved fields:

```text
8_resolved_expression_type
8_resolved_option_right
8_resolved_dominant_horizon
8_resolved_selected_contract_ref
8_resolved_contract_fit_score
8_resolved_expression_confidence_score
8_resolved_no_option_reason_codes
8_resolved_reason_codes
```

V1 expression types:

```text
long_call
long_put
no_option_expression
```

V1 option rights:

```text
call
put
none
```

## Score families

Layer 8 score families use the `8_` prefix and `<horizon>` suffix for horizon-aware scalar scores.

```text
8_option_expression_eligibility_score_<horizon>
8_option_expression_direction_score_<horizon>
8_option_contract_fit_score_<horizon>
8_option_liquidity_fit_score_<horizon>
8_option_iv_fit_score_<horizon>
8_option_greek_fit_score_<horizon>
8_option_reward_risk_score_<horizon>
8_option_theta_risk_score_<horizon>
8_option_fill_quality_score_<horizon>
8_option_expression_confidence_score_<horizon>
```

Semantics:

- eligibility is high-is-good and means the option expression is admissible under Layer 7 thesis, policy, option-chain, liquidity, IV, and risk constraints;
- direction is signed: positive call-side/bullish expression, negative put-side/bearish expression, near zero no-option expression;
- contract fit is high-is-good and summarizes DTE, delta/Greeks, IV, liquidity, fill quality, and reward/risk;
- theta risk is high-is-bad;
- expression confidence is high-is-good and remains offline model confidence, not order approval.

## Plan payload

`option_expression_plan` may include:

```text
selected_expression_type
selected_option_right
dominant_horizon
selected_contract
option_chain_snapshot_ref
option_quote_available_time
underlying_quote_snapshot_ref
underlying_reference_price
replay_context
contract_constraints
premium_risk_plan
underlying_thesis_ref
underlying_path_assumptions
reason_codes
diagnostics
```

`selected_contract` is a point-in-time contract reference and diagnostics payload. It is not a broker order. `contract_constraints` are model constraints, not routing instructions.

## Deterministic V1 scaffold

The local deterministic scaffold lives in:

```text
src/models/model_08_option_expression/
```

It implements:

- Layer 7 bullish thesis -> long-call candidate search;
- Layer 7 bearish thesis or no-direct-short bearish thesis -> long-put candidate search;
- Layer 7 `maintain` / `no_trade`, policy blocks, or pending option exposure -> `no_option_expression`;
- hard filters for right, bid/ask/mid, DTE range, preferred absolute delta range, stale quote age, volume/open interest, spread, adjusted-contract exclusion, and target-range moneyness guardrails;
- DTE / delta / Greeks / IV / liquidity / reward-risk scoring with per-candidate hard-filter reason codes;
- offline label join helpers and leakage assertions.

Fixture tests live in:

```text
tests/test_option_expression_model.py
```

## V1 DTE / delta policy

V1 uses conservative ranges rather than exact DTE points:

```text
5min / 15min thesis -> preferred_dte_range = 3-7, no 0DTE
60min / same-session thesis -> preferred_dte_range = 7-14
390min / one-session thesis -> preferred_dte_range = 7-21
multi-day thesis -> preferred_dte_range = 21-45
```

V1 avoids deep OTM lottery contracts. Preferred absolute delta starts around `0.35-0.65`; future learned contract-fit models may adjust this by path quality, expected move, IV, liquidity, and theta pressure.

Layer 7 target/range fields constrain moneyness when the target range is directionally coherent: bullish call strikes may not sit above `target_price_high`; bearish put strikes may not sit below `target_price_low`. Candidates outside the guardrail carry `strike_outside_underlying_target_range` and cannot be selected in V1.

## Labels and evaluation

Offline label families may include:

```text
realized_option_return_5min
realized_option_return_15min
realized_option_return_60min
realized_option_return_390min
realized_option_max_favorable_excursion_390min
realized_option_max_adverse_excursion_390min
target_premium_hit_before_stop_label_390min
premium_stop_hit_before_target_label_390min
option_spread_adjusted_return_390min
selected_contract_regret_vs_best_candidate_390min
realized_option_mid_return_<horizon>
realized_option_bid_exit_return_<horizon>
realized_option_spread_cost_<horizon>
realized_iv_change_<horizon>
realized_theta_decay_<horizon>
realized_delta_path_exposure_<horizon>
underlying_target_hit_but_option_lost_label_<horizon>
option_no_expression_opportunity_cost_<horizon>
option_expression_avoided_loss_value_<horizon>
candidate_contract_utility_curve_<horizon>
```

Evaluation must prove that Layer 8 improves option-expression outcomes versus simpler baselines:

1. no option expression;
2. underlying-only Layer 7 expression;
3. naive ATM nearest-expiration call/put from Layer 7 direction;
4. fixed-delta/fixed-DTE expression;
5. Layer 8 full contract-fit and risk-aware expression.

Promotion remains deferred until real point-in-time option feeds, calibration, leakage controls, baseline improvement, and stability evidence pass review.

## Invariants

```text
option expression != broker order
contract_ref != broker order id
selected_contract != send order
contract constraints != route / time-in-force
premium risk plan != account mutation
expression confidence != final approval
Layer 8 offline plan != live execution
```

`trading-execution` remains the owner of live/paper broker mutation.
