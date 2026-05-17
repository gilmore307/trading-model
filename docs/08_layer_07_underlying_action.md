# Layer 07 — UnderlyingActionModel

<!-- ACTIVE_LAYER_REVISION -->
Status: active architecture revision. Conceptual Layer 7; current physical implementation surface remains `src/models/model_07_underlying_action/` until code/SQL surfaces are renamed.

Active boundary: Layer 7 converts Layer 6 target holding-state projection into an offline direct-underlying action thesis: eligibility, planned action type, exposure-adjustment thesis, entry/target/stop/time assumptions, and handoff to Layer 8 trading guidance.

It may describe a direct stock/ETF plan, but it is not broker execution and does not select option contracts. Layer 8 composes the final offline trading guidance candidate; Layer 9 may later cap/block/reduce/flatten that candidate for event risk.
<!-- /ACTIVE_LAYER_REVISION -->


Status: accepted Layer 7 design route; deterministic scaffold implemented in `src/models/model_07_underlying_action/`; production validation pending.

## Purpose

`UnderlyingActionModel` is Layer 7. It consumes Layer 5 `alpha_confidence_vector`, Layer 6 `position_projection_vector`, point-in-time current/pending underlying exposure, quote/liquidity state, and risk/policy gates to produce an `underlying_action_plan` and supporting `underlying_action_vector`.

Layer 7 answers:

- Is the current opportunity eligible for direct stock/ETF expression?
- If using the underlying, should the offline plan open, increase, reduce, close, cover, maintain, or avoid a position?
- How much exposure should this planned adjustment express before execution-side review?
- What entry, target, stop, thesis-invalidation, and time-stop assumptions define the underlying thesis?
- What side-neutral price-path assumptions should Layer 8 use when evaluating option expression?

Layer 7 does **not** place orders, route orders, choose order type, mutate broker/account state, or select option contracts. Its action type is a planned/offline action type, not an execution instruction. Live/paper execution remains in `trading-execution`.

## Position in the stack

The accepted downstream chain is:

```text
Layer 5: AlphaConfidenceModel
  -> alpha_confidence_vector

Layer 6: PositionProjectionModel
  -> position_projection_vector

Layer 7: UnderlyingActionModel
  -> underlying_action_plan / underlying_action_vector

Layer 8: TradingGuidanceModel / OptionExpressionModel
  -> option_expression_plan / expression_vector

trading-execution
  -> broker/account execution, orders, fills, reconciliation, safety controls
```

Layer 5 asks whether event-conditioned alpha exists. Layer 6 maps adjusted alpha to target holding state. Layer 7 maps target holding state to a direct underlying action thesis. Layer 8 may use that thesis to choose an option expression. `trading-execution` is the only owner of real order placement.

## Names

Accepted names:

```text
Model class: UnderlyingActionModel
Stable id: underlying_action_model
Conceptual layer id: model_07_underlying_action
Current physical layer id: model_07_underlying_action
Primary output: underlying_action_plan
Score/vector output: underlying_action_vector
```

Avoid `ExecutionModel`, `final_action`, `order_instruction`, and `execution_instruction` names for Layer 7. Layer 7 may say `planned_underlying_action_type = increase_long`; it may not say `send_order = true`.

## Core responsibilities

Layer 7 owns six responsibilities:

1. Decide whether direct stock/ETF expression is currently allowed.
2. Resolve Layer 6 position gap into a planned underlying action type.
3. Convert alpha, projection confidence, costs, risk budget, stability, and liquidity into planned action intensity.
4. Build the direct-underlying entry, target, stop, thesis-invalidation, and time-stop plan.
5. Emit a side-neutral underlying price-path thesis.
6. Hand that thesis to Layer 8 for option-expression evaluation without choosing strike, DTE, delta, or contract.

Layer 7 is therefore a policy/strategy translation layer:

```text
current state + confidence + target exposure
  -> policy gates
  -> planned underlying action type
  -> planned exposure change
  -> entry/target/stop/time thesis
  -> Layer 8 trading-guidance handoff
```

## Inputs

Production inference inputs must be point-in-time only:

```text
decision_time
available_time
tradeable_time
target_candidate_id
symbol_ref
alpha_confidence_vector_ref
position_projection_vector_ref
current_underlying_position_state_ref
pending_underlying_order_state_ref
underlying_quote_state_ref
underlying_liquidity_state_ref
underlying_borrow_state_ref
risk_budget_state_ref
policy_gate_ref
model_version
state_version
```

Training/evaluation inputs may include future outcomes as labels, but labels must stay outside inference features.

### Input A - Layer 5 final adjusted alpha

Layer 7 may consume Layer 5 score families directly or through Layer 5 refs when it needs the alpha/path/risk terms behind an action plan:

```text
5_alpha_direction_score_<horizon>
5_alpha_strength_score_<horizon>
5_expected_return_score_<horizon>
5_alpha_confidence_score_<horizon>
5_signal_reliability_score_<horizon>
5_path_quality_score_<horizon>
5_reversal_risk_score_<horizon>
5_drawdown_risk_score_<horizon>
5_alpha_tradability_score_<horizon>
```

Layer 5 remains alpha confidence only. A high alpha score is not itself a trade.

### Input B - Layer 6 position projection

Layer 7 consumes Layer 6 target holding-state projection:

```text
6_target_position_bias_score_<horizon>
6_target_exposure_score_<horizon>
6_current_position_alignment_score_<horizon>
6_position_gap_score_<horizon>
6_position_gap_magnitude_score_<horizon>
6_expected_position_utility_score_<horizon>
6_cost_to_adjust_position_score_<horizon>
6_risk_budget_fit_score_<horizon>
6_position_state_stability_score_<horizon>
6_projection_confidence_score_<horizon>
```

Layer 7 should prefer Layer 6 resolved handoff fields when available:

```text
6_dominant_projection_horizon
6_horizon_conflict_state
6_resolved_target_exposure_score
6_resolved_position_gap_score
6_projection_resolution_confidence_score
6_horizon_resolution_reason_codes
```

Layer 6 projection does not choose instrument, quantity, order type, or final action. Layer 7 translates it into an offline direct-underlying plan.

### Input C - current and pending underlying exposure

Layer 7 must account for pending underlying exposure to avoid repeated planned adjustments:

```text
effective_current_underlying_exposure_score
= current_underlying_exposure_score
  + pending_underlying_exposure_score * pending_fill_probability_estimate
```

The Layer 7 underlying gap is:

```text
underlying_exposure_gap_score
= target_underlying_exposure_score
  - effective_current_underlying_exposure_score
```

The exposure plan must preserve all of these axes:

```text
current_underlying_exposure_score
pending_adjusted_underlying_exposure_score
effective_current_underlying_exposure_score
target_underlying_exposure_score
underlying_exposure_gap_score
planned_incremental_exposure_score
```

`target_underlying_exposure_score` is the ideal final direct-underlying exposure. `planned_incremental_exposure_score` is the current offline plan's proposed change before execution-side review.

### Input D - underlying quote, liquidity, and borrow state

Eligible point-in-time market state includes:

```text
reference_price
bid_price
ask_price
mid_price
spread_bps
volume
dollar_volume
atr_or_realized_volatility
halt_status
short_borrow_status
trading_restriction_state
```

Layer 7 uses these to evaluate direct-underlying liquidity and entry quality. Option-chain fields stay out of Layer 7.

### Input E - risk and policy state

Eligible risk/policy inputs include:

```text
risk_budget_state
portfolio_exposure_state
symbol_concentration_state
kill_switch_state
max_symbol_exposure
max_daily_loss_state
underlying_event_policy_block_state
```

`underlying_event_policy_block_state` is policy-derived. Layer 9 event-risk context does not directly issue hard trade blocks; event risk may be translated into policy state by event-risk/policy logic before trading guidance consumes it.

## V1 horizons

Layer 7 V1 uses the synchronized horizons already used by Layers 5 and 6:

```text
5min
15min
60min
390min
```

`390min` means one regular US equity session-equivalent horizon measured in tradable minutes. Layer 7 must document same-session versus next-session-close label resolution and use purge/embargo controls for overlapping labels.

## Planned action types

Layer 7 V1 planned action types are:

```text
open_long
increase_long
reduce_long
close_long
open_short
increase_short
reduce_short
cover_short
maintain
no_trade
bearish_underlying_path_but_no_short_allowed
```

`maintain` and `no_trade` are deliberately separate:

- `maintain` means an existing state is still aligned or not worth adjusting.
- `no_trade` means no new direct-underlying operation should be initiated.

Use these position-state names in documentation and code:

```text
flat / no position
long position
short position
```

Do not use ambiguous `empty position` / `short position` wording that can confuse flat with short.

Opposite-exposure cases should be conservative in V1. Prefer reason codes such as:

```text
opposite_exposure_detected
close_then_reassess_candidate
reassess_opposite_expression_after_close
```

Do not make one-step long-to-short or short-to-long reversal the default action. Execution-side policy and risk review must confirm any actual reversal.

## Hard gates and soft gates

Layer 7 splits gate logic into hard gates and soft gates.

### Hard gates

A failed hard gate blocks direct-underlying action initiation or forces a reviewed risk-reduction-only route:

```text
halt_status_not_active
kill_switch_active
risk_budget_hard_block
liquidity_hard_fail
symbol_trading_restricted
short_borrow_failed_for_direct_short
underlying_event_hard_block
missing_required_point_in_time_state
```

Typical output for blocked new exposure is:

```text
planned_underlying_action_type = no_trade
```

For existing positions, a hard gate may still allow `reduce_long`, `close_long`, `reduce_short`, or `cover_short` when risk policy explicitly permits risk reduction. It still does not send an order.

### Soft gates

Soft gates reduce action intensity, change entry style, or favor waiting:

```text
alpha_confidence_marginal
projection_confidence_marginal
position_gap_small
cost_pressure_high
entry_quality_weak
reversal_risk_elevated
drawdown_risk_elevated
path_quality_weak
liquidity_marginal
```

A soft-gate failure should usually lower `planned_incremental_exposure_score`, choose `wait_for_pullback`, or produce `maintain` / `no_trade` with reason codes rather than pretending the target exposure is immediately tradable.

## Position-gap to action resolution

Layer 7 resolves action using effective exposure, not raw current position alone:

| Current direct-underlying state | `underlying_exposure_gap_score` | Planned action |
|---|---:|---|
| flat | materially positive | `open_long` |
| long position | materially positive | `increase_long` |
| long position | near zero | `maintain` |
| long position | materially negative but still positive target | `reduce_long` |
| long position | target near zero or opposite | `close_long` plus reason code if opposite exposure is detected |
| flat | materially negative and direct short allowed | `open_short` |
| flat | materially negative and direct short not allowed | `bearish_underlying_path_but_no_short_allowed` |
| short position | materially negative | `increase_short` |
| short position | near zero | `maintain` |
| short position | materially positive but still negative target | `reduce_short` |
| short position | target near zero or opposite | `cover_short` plus reason code if opposite exposure is detected |
| any | hard blocked | `no_trade` or risk-reduction-only planned action |
| any | gap too small / cost not worth it | `maintain` if state exists, otherwise `no_trade` |

The gap threshold is configurable and should be validated per horizon and liquidity bucket.

## Trade intensity and planned sizing

Layer 7 converts gap and confidence into action intensity. A deterministic V1 scaffold can use:

```text
trade_intensity
= abs(underlying_exposure_gap_score)
  * alpha_confidence
  * projection_confidence
  * signal_reliability
  * risk_budget_fit
  * position_state_stability
  * liquidity_fit
  * (1 - cost_to_adjust_position)
  * (1 - drawdown_risk)
  * (1 - reversal_risk)
```

The result informs:

```text
planned_incremental_exposure_score
planned_notional_usd
planned_quantity
scale_in_policy
```

`planned_quantity` and `planned_notional_usd` are pre-execution suggestions. They are not final order size. `trading-execution` may recut the quantity based on real-time bid/ask, liquidity, partial fills, buying power, lot constraints, risk limits, and order state.

## Entry plan

Layer 7 may emit entry styles such as:

```text
marketable_review
limit_near_mid
limit_or_pullback
wait_for_pullback
wait_for_breakout_confirmation
maintain_existing_entry
no_entry
```

Entry fields should be side-neutral:

```text
reference_price
expected_entry_price
worst_acceptable_entry_price
do_not_chase_price
entry_price_limit_direction
entry_expiration_time
entry_quality_score
```

For a long plan, `worst_acceptable_entry_price` is normally an upper bound. For a short plan, it is normally a lower bound. `action_side` owns the interpretation.

Layer 7 should avoid entry assumptions that backtests cannot actually fill. Entry plans need fill-probability labels and regret checks against market, limit, pullback, wait, and no-trade alternatives.

## Price-path expectation

Layer 7 outputs a side-neutral underlying thesis for direct-underlying and option-expression consumers:

```text
underlying_path_direction
expected_holding_time_minutes
expected_holding_time_label
expected_target_price
target_price_low
target_price_high
expected_favorable_move_pct
expected_adverse_move_pct
path_quality_score
reversal_risk_score
drawdown_risk_score
```

For long plans, favorable movement is price up. For short plans, favorable movement is price down. The raw field names stay favorable/adverse so downstream logic does not reverse `downside` semantics incorrectly.

`expected_target_price` is a thesis anchor, not a guarantee. It must be derived from point-in-time alpha expected return, path quality, drawdown/reversal risk, market volatility, and current price state. It must not use future highs/lows/fills as inference inputs.

## Risk plan

Layer 7 emits a direct-underlying risk thesis:

```text
partial_take_profit_price
take_profit_price
stop_loss_price
thesis_invalidation_price
time_stop_minutes
expected_favorable_move_pct
expected_adverse_move_pct
reward_risk_ratio
risk_plan_reason_codes
```

`stop_loss_price` and `take_profit_price` describe the offline plan. They are not broker stop orders or limit orders. Execution-side systems decide whether and how any stop/limit order is staged.

## Handoff to Layer 8

Layer 7 is the underlying-thesis provider for option expression. Handoff fields should be enough for Layer 8 to evaluate option contracts without Layer 7 crossing the contract-selection boundary:

```text
underlying_path_direction
expected_entry_price
expected_target_price
target_price_low
target_price_high
stop_loss_price
thesis_invalidation_price
expected_holding_time_minutes
path_quality_score
reversal_risk_score
drawdown_risk_score
expected_favorable_move_pct
expected_adverse_move_pct
entry_price_assumption
```

Layer 7 may not output:

```text
option_symbol
option_right
strike
expiration
DTE
delta
theta
vega
specific_contract_ref
option_order_type
```

Those belong to Layer 8 and execution-side systems.

## Core output contract

The primary output is `underlying_action_plan`. The V1 score/vector output `underlying_action_vector` exposes 10 per-horizon score families:

```text
7_underlying_trade_eligibility_score_<horizon>
7_underlying_action_direction_score_<horizon>
7_underlying_trade_intensity_score_<horizon>
7_underlying_entry_quality_score_<horizon>
7_underlying_expected_return_score_<horizon>
7_underlying_adverse_risk_score_<horizon>
7_underlying_reward_risk_score_<horizon>
7_underlying_liquidity_fit_score_<horizon>
7_underlying_holding_time_fit_score_<horizon>
7_underlying_action_confidence_score_<horizon>
```

Physical SQL column names must avoid unquoted numeric-leading identifiers unless the storage contract explicitly quotes them. These names are canonical vector payload tokens and may live inside JSONB/vector payloads.

## Core score semantics

| Field family | Range | Directionality | High value means |
|---|---:|---|---|
| `7_underlying_trade_eligibility_score_<horizon>` | `[0, 1]` | high-is-good | Direct underlying expression passes point-in-time gate quality for this horizon. |
| `7_underlying_action_direction_score_<horizon>` | `[-1, 1]` | signed | Planned direct-underlying side; positive = long-side plan, negative = short-side plan, near zero = maintain/no-trade. |
| `7_underlying_trade_intensity_score_<horizon>` | `[0, 1]` | high-is-more | Planned adjustment intensity after confidence, risk, cost, stability, and liquidity compression. |
| `7_underlying_entry_quality_score_<horizon>` | `[0, 1]` | high-is-good | Current or planned entry quality supports the action. |
| `7_underlying_expected_return_score_<horizon>` | `[-1, 1]` | signed utility | Expected direct-underlying favorable move / return quality after context adjustment. |
| `7_underlying_adverse_risk_score_<horizon>` | `[0, 1]` | high-is-bad | Expected adverse move / stop-risk pressure for the planned underlying action. |
| `7_underlying_reward_risk_score_<horizon>` | `[0, 1]` | high-is-good | Planned reward/risk quality of the direct-underlying thesis. |
| `7_underlying_liquidity_fit_score_<horizon>` | `[0, 1]` | high-is-good | Direct underlying liquidity/spread supports the planned adjustment. |
| `7_underlying_holding_time_fit_score_<horizon>` | `[0, 1]` | high-is-good | Planned holding time is compatible with alpha, projection, liquidity, and event context. |
| `7_underlying_action_confidence_score_<horizon>` | `[0, 1]` | high-is-good | Confidence in the complete direct-underlying action plan. |

## Resolved plan fields

Layer 7 also needs resolved plan fields so downstream consumers do not re-solve per-horizon action conflicts:

```text
7_resolved_underlying_action_type
7_resolved_action_side
7_resolved_dominant_horizon
7_resolved_trade_eligibility_score
7_resolved_trade_intensity_score
7_resolved_entry_quality_score
7_resolved_action_confidence_score
7_resolved_reason_codes
```

Resolved fields are handoff/plan fields, not core scalar score-family rows. They summarize the chosen underlying thesis and remain offline.

## Example output

```json
{
  "model_layer": "layer_07_underlying_action",
  "model_name": "UnderlyingActionModel",
  "output_name": "underlying_action_plan",
  "symbol": "AAPL",
  "available_time": "2026-05-07T10:30:00-04:00",
  "tradeable_time": "2026-05-07T10:31:00-04:00",
  "action": {
    "planned_underlying_action_type": "increase_long",
    "action_side": "long",
    "dominant_horizon": "390min",
    "trade_eligibility_score": 0.74,
    "action_intensity_score": 0.42,
    "action_confidence_score": 0.68
  },
  "exposure_plan": {
    "target_underlying_exposure_score": 0.28,
    "current_underlying_exposure_score": 0.10,
    "pending_adjusted_underlying_exposure_score": 0.07,
    "effective_current_underlying_exposure_score": 0.17,
    "underlying_exposure_gap_score": 0.11,
    "planned_incremental_exposure_score": 0.07,
    "planned_notional_usd": 6400,
    "planned_quantity": 35
  },
  "entry_plan": {
    "entry_style": "limit_or_pullback",
    "reference_price": 183.20,
    "expected_entry_price": 183.00,
    "worst_acceptable_entry_price": 184.20,
    "do_not_chase_price": 184.80,
    "entry_price_limit_direction": "upper_bound_for_long",
    "entry_expiration_time": "2026-05-07T11:00:00-04:00"
  },
  "price_path_expectation": {
    "underlying_path_direction": "bullish",
    "expected_holding_time_minutes": 390,
    "expected_holding_time_label": "1_session",
    "expected_target_price": 191.50,
    "target_price_low": 188.80,
    "target_price_high": 193.20,
    "expected_favorable_move_pct": 0.045,
    "expected_adverse_move_pct": -0.022
  },
  "risk_plan": {
    "partial_take_profit_price": 188.80,
    "take_profit_price": 191.50,
    "stop_loss_price": 179.20,
    "thesis_invalidation_price": 178.60,
    "reward_risk_ratio": 2.05,
    "time_stop_minutes": 390
  },
  "handoff_to_layer_8": {
    "underlying_path_direction": "bullish",
    "expected_entry_price": 183.00,
    "expected_target_price": 191.50,
    "target_price_low": 188.80,
    "target_price_high": 193.20,
    "stop_loss_price": 179.20,
    "expected_holding_time_minutes": 390,
    "path_quality_score": 0.66,
    "reversal_risk_score": 0.24,
    "drawdown_risk_score": 0.31
  },
  "reason_codes": [
    "positive_resolved_position_gap",
    "alpha_confidence_passed",
    "risk_budget_fit_passed",
    "cost_to_adjust_acceptable",
    "liquidity_passed",
    "390min_projection_dominant"
  ]
}
```

## Internal decomposition

Layer 7 is decomposed into these components:

### 7A - TradeEligibilityGate

Splits hard gates from soft gates and emits trade eligibility score, block state, and reason codes.

### 7B - HorizonAndActionResolver

Resolves conflicting Layer 5/6 per-horizon signals and chooses the dominant Layer 7 action horizon. It must not simply average a short-term long bias with a longer-term short bias.

### 7C - UnderlyingActionResolver

Maps effective exposure gap and current direct-underlying state to a planned action type.

### 7D - TradeIntensitySizer

Calculates planned incremental exposure, planned notional, planned quantity, and scale-in policy from gap, confidence, risk, stability, liquidity, and cost terms.

### 7E - EntryPlanBuilder

Builds side-neutral entry assumptions, worst acceptable entry price, chase limits, entry style, and entry expiry.

### 7F - PricePathProjector

Builds target price, target range, expected favorable/adverse move, holding-time expectation, and path quality assumptions.

### 7G - RiskPlanBuilder

Builds take-profit, partial take-profit, stop, thesis-invalidation, time-stop, and reward/risk fields.

### 7H - LayerEightHandoffBuilder

Packages the underlying thesis for option-expression evaluation without leaking option contract choices into Layer 7.

### 7I - UnderlyingActionComposer

Composes `underlying_action_plan`, `underlying_action_vector`, resolved fields, diagnostics refs, reason codes, and acceptance evidence refs.

## Labels and outcomes

Layer 7 labels evaluate plan quality rather than raw direction prediction. Candidate labels include:

```text
realized_underlying_return_after_entry_<horizon>
realized_net_underlying_utility_<horizon>
planned_entry_fill_probability_label
entry_plan_regret_label
action_type_regret_vs_best_action
entry_price_hit_label
target_price_hit_before_stop_label
stop_price_hit_before_target_label
realized_max_favorable_excursion_<horizon>
realized_max_adverse_excursion_<horizon>
realized_holding_time_to_target
realized_holding_time_to_stop
action_bucket_realized_pnl
no_trade_opportunity_cost
bad_trade_avoidance_value
no_trade_missed_positive_utility_rate
no_trade_avoided_negative_utility_rate
no_trade_net_utility_vs_trade_baseline
slippage_adjusted_return
spread_adjusted_return
reward_risk_realized_ratio
```

Labels must be materialized only in training/evaluation datasets and must not be joined into `underlying_action_plan` at inference time.

## Training route

Layer 7 should be trained or calibrated in stages:

1. **Deterministic policy scaffold**: map Layer 5/6 scores plus quote/risk gates to planned action, intensity, entry, target, stop, and time-stop.
2. **Candidate action utility evaluation**: evaluate `no_trade`, `maintain`, open/increase/reduce/close candidates, and direct short candidates where allowed.
3. **Entry and risk-plan calibration**: learn fill probability, target-before-stop, stop-before-target, MFE/MAE, and reward/risk quality.
4. **Plan confidence calibration**: calibrate `7_underlying_action_confidence_score_<horizon>` by out-of-sample plan utility buckets.
5. **Layer 8 handoff validation**: prove that Layer 7 price-path assumptions improve option-expression selection versus raw alpha/projection-only baselines.

Do not train Layer 7 from in-sample upstream model outputs. Upstream vectors consumed by Layer 7 training must be generated with rolling/cross-fitted point-in-time discipline.

## Baselines and validation

Layer 7 should prove incremental value over:

1. no-trade baseline;
2. always-trade-on-alpha baseline;
3. Layer 7 gap-only threshold baseline;
4. market-entry baseline without entry planning;
5. target/stop-less holding-time baseline;
6. deterministic policy scaffold;
7. calibrated candidate-action utility model;
8. full Layer 7 with Layer 7 handoff fields.

Validation must separately check:

- eligibility: high trade eligibility maps to better realized net utility;
- direction/action: planned action buckets outperform incompatible alternatives;
- intensity: trade-intensity buckets are monotonic with realized utility and risk;
- entry: entry plans are fillable and improve over market/pullback/no-trade alternatives;
- target/stop: target-before-stop improves with high reward/risk score;
- risk: stops and thesis invalidation limit realized MAE without excessive good-trade truncation;
- confidence: action-confidence buckets are calibrated out-of-sample;
- no-trade: no-trade avoids bad trades without unacceptable missed-positive-utility cost;
- handoff: Layer 8 option expression improves when it uses Layer 7 price-path assumptions;
- leakage: all feature rows obey `available_time <= decision_time`, and labels are isolated from inference features.

## Boundary rules

Keep these semantics separate:

```text
alpha confidence != planned action
position gap != trade instruction
target exposure != planned quantity
planned quantity != broker order quantity
trade eligibility != final approval
entry plan != order type
stop_loss_price != broker stop order
take_profit_price != broker limit order
underlying price-path thesis != guaranteed outcome
underlying action plan != option expression
underlying action plan != live execution
```

Layer 7 must not:

- emit broker order fields such as `order_type`, `route`, `time_in_force`, `send_order`, `replace_order`, `cancel_order`, or `broker_order_id`;
- choose option contract, strike, DTE, delta, Greeks, or specific option symbol;
- read option chains as default inference features;
- mutate broker/account state;
- bypass execution/risk approval;
- use future prices, future fills, future PnL, future slippage, or future event revisions as inference inputs;
- treat `planned_quantity` or `planned_notional_usd` as final order size.

## V1 implementation route

Current local scaffold status:

1. Deterministic `model_07_underlying_action` scaffold exists using Layer 5/6 fixture vectors, quote/liquidity fixtures, and risk/policy fixtures.
2. Effective-current-underlying-exposure calculation with pending fill probability is implemented.
3. Hard-gate/soft-gate decision trace and planned action resolver are implemented.
4. Entry, price-path, risk-plan, and Layer 8 handoff builders are implemented.
5. Fixture tests cover maintain vs no_trade, pending-exposure avoidance, side-neutral price fields, conservative opposite-exposure handling, and no order/option-field leakage.
6. Local evaluation-label helper covers target-before-stop, entry fill probability, no-trade opportunity/avoidance, slippage/spread-adjusted return, and realized reward/risk.
7. Shared names were promoted through `trading-manager` before cross-repository dependence.

Remaining implementation hardening is real-data calibration/evaluation, not contract-definition work.

## Acceptance gates

Layer 7 design/implementation is not accepted for production until:

- docs, registry names, and score families are synchronized;
- deterministic scaffold passes fixture tests;
- hard/soft gates are audited with reason-code evidence;
- maintain and no_trade semantics are separately tested;
- pending-adjusted effective exposure prevents duplicate planned adjustments;
- side-neutral entry/risk fields work for long and short plans;
- no broker order fields or option-contract fields leak into Layer 7 outputs;
- plan-quality labels are point-in-time and separated from inference features;
- walk-forward validation beats the accepted baselines;
- Layer 8 handoff fields improve option-expression evaluation or are explicitly deferred.