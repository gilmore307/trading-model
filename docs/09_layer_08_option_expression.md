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
8_resolved_contract_ref
8_resolved_expression_confidence_score
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
- no-option-expression policy blocks;
- DTE / delta / Greeks / IV / liquidity / reward-risk scoring;
- offline label join helpers and leakage assertions.

Fixture tests live in:

```text
tests/test_option_expression_model.py
```

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
```

Evaluation must prove that Layer 8 improves option-expression outcomes versus simpler baselines:

1. no option expression;
2. naive ATM nearest-expiration call/put from Layer 7 direction;
3. fixed-delta/fixed-DTE expression;
4. Layer 8 full contract-fit and risk-aware expression.

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
