# Layer 07 — PositionProjectionModel

Status: accepted Layer 7 design route; deterministic V1 scaffold implemented in `src/models/model_07_position_projection/`.

## Purpose

`PositionProjectionModel` is Layer 7. It consumes the final adjusted Layer 5 `alpha_confidence_vector` plus point-in-time current/pending position state, position-level friction, portfolio exposure context, risk-budget context, and policy gates to produce the `position_projection_vector`.

Layer 7 answers:

- What target holding/exposure state does the current alpha imply?
- Is the current plus pending position already aligned with that target state?
- How large and in which direction is the position gap?
- Is changing the position state expected to have positive risk-adjusted net utility?
- Are costs, liquidity, concentration, drawdown state, and risk budget compatible with the target exposure?
- Which horizon should dominate the handoff when per-horizon projections conflict?

Layer 7 does **not** answer buy/sell/hold, open/close/reverse, instrument choice, option-contract choice, order type, routing, or live/paper execution questions. It projects target position state only. Layer 8 owns the direct-underlying planned action thesis; Layer 9 owns option expression. Broker mutation remains outside `trading-model`.

## Training Sample Granularity

Layer 7 training should use dense minute-level position-projection rows whenever point-in-time Layer 5 alpha, Layer 6 policy state, and current/pending position context can be constructed. Live runtime may call Layer 7 only when an active position or routed candidate needs a fresh projection, but training only on those trigger minutes would hide aligned, no-gap, low-utility, and near-threshold states that later Layer 8 action planning needs to be calibrated.

The Layer 7 training row universe is not `minute x every listed symbol`. It is every eligible minute-level projection state for:

- active positions;
- routed or simulated candidate positions with point-in-time current/pending exposure context;
- flat/no-position control rows where the model must learn that target exposure should remain zero;
- near-threshold rows that would be easy to overtrade without cost and risk-budget discipline.

Action triggers, exposure-change thresholds, and downstream Layer 8 handoff decisions are calibration/routing policies after projection. They must not decide which historical minutes Layer 7 is allowed to learn from.

## Projection Evidence Boundary

A changed target exposure is not by itself a position adjustment. Layer 7 may update projected target holding state every minute, but it only emits the evidence Layer 8 needs to decide whether an adjustment plan is justified:

- resolved target exposure;
- resolved position gap;
- expected position utility;
- cost-to-adjust pressure;
- risk-budget fit;
- projection stability and confidence;
- pending-adjusted effective exposure;
- horizon conflict state and resolution reasons.

Layer 7 must not emit `maintain`, `no_trade`, `open`, `increase`, `reduce`, `close`, or `cover`. Those are Layer 8 planned-action outcomes. Layer 7's job is to make target exposure and adjustment pressure explicit without turning minute-level projection changes into action policy.

## Position and input chain

The accepted chain is:

```text
alpha_confidence_vector
+ current_position_state
+ pending_position_state
+ position-level friction context
+ portfolio exposure context
+ risk-budget context
+ point-in-time policy gates
  -> PositionProjectionModel
  -> position_projection_vector
```

Layer 5 asks whether event-conditioned alpha exists. Layer 7 maps that alpha to target holding state under current account/portfolio context. Layer 8 maps the projected holding state to a planned direct-underlying action thesis.

```text
Layer 5: alpha confidence
Layer 7: projected target position state
Layer 8: direct-underlying planned action boundary
```

## Names

Accepted names:

```text
Model class: PositionProjectionModel
Stable id: position_projection_model
Conceptual layer id: model_07_position_projection
Physical layer id: model_07_position_projection
Conceptual output: position_projection_vector
```

Avoid signal-model or signal-vector naming for Layer 7. `signal` language is too close to buy/sell/hold operations and blurs the accepted boundary.

## Inputs

Production inference inputs must be point-in-time only:

```text
decision_time
available_time
tradeable_time
target_candidate_id
horizons
alpha_confidence_vector_ref
current_position_state_ref
pending_position_state_ref
portfolio_exposure_state_ref
risk_budget_state_ref
position_level_friction_ref
policy_gate_ref
model_version
state_version
```

Training/evaluation inputs may include future outcomes as labels, but those labels must stay outside inference features.

### Input A - Layer 5 final adjusted alpha

Layer 7 consumes the final adjusted Layer 5 `alpha_confidence_vector` by default:

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

Base/unadjusted Layer 5 `5_base_*` diagnostics may be retained as explainability refs, but they must not be treated as competing default trading inputs.

### Input B - current position state

Layer 7 is the first model layer allowed to use current position state as an inference input. Eligible current-position evidence includes:

```text
current_position_direction
current_position_exposure
current_position_age
current_position_entry_ref
current_position_unrealized_risk
current_position_liquidity_state
current_position_concentration_state
```

`current_position_exposure` is an abstract normalized exposure measure, not share count, contract count, or order quantity.

### Input C - pending position state

Pending exposure must be included so Layer 7 does not repeatedly project already-covered adjustments:

```text
pending_exposure_direction
pending_exposure_size
pending_order_age
pending_order_fill_probability_estimate
pending_order_cancellable_state
pending_order_risk_state
```

Layer 7 uses an effective exposure concept:

```text
effective_current_exposure
= current_position_exposure
+ pending_exposure_size * pending_order_fill_probability_estimate
```

`effective_current_exposure` is a model-local diagnostic/input construct. It is not an order instruction.

### Input D - position-level friction context

Layer 7 may use generic position-level friction that affects whether changing exposure is worthwhile:

```text
spread_cost_estimate
slippage_cost_estimate
fee_cost_estimate
turnover_cost_estimate
liquidity_capacity_score
```

`7_cost_to_adjust_position_score_<horizon>` should represent cost pressure for changing the current position gap, not raw market cost alone. A high spread should not heavily penalize a row when `position_gap` is near zero.

### Input E - expression-specific friction hints

Expression-specific costs may be retained as soft context or diagnostics, but they must not cause Layer 7 to choose or reject a specific instrument:

```text
borrow_cost_hint
financing_cost_hint
option_expression_cost_hint
```

Borrow and financing costs are especially boundary-sensitive. If Layer 7 models abstract risk exposure, poor stock borrow should not automatically zero short exposure because Layer 8 may express the same exposure through options.

### Input F - risk budget and portfolio context

Eligible risk/portfolio context includes:

```text
single_name_exposure_limit
sector_exposure_limit
portfolio_gross_exposure
portfolio_net_exposure
correlation_concentration_score
drawdown_state
volatility_budget_state
risk_budget_available_score
kill_switch_state
```

Risk gates may compress target exposure and reduce risk-budget fit. They do not directly produce final action, forced liquidation, or order cancellation instructions.

## Inputs explicitly excluded

Layer 7 inference must not use:

```text
future returns
future fills
future PnL
future slippage
future option path
future broker execution result
post-trade outcome labels
```

Layer 7 also must not use expression-selection inputs as default model features:

```text
option_contract
option_symbol
strike
DTE
delta
gamma
theta
vega
specific option bid/ask choice
order_type
routing_destination
broker_order_id
```

These belong to Layer 8 underlying-action work, Layer 9 option-expression/trading-guidance work, or execution-side repositories.

## Internal structure

Layer 7 V1 uses auditable submodules before any broad learned utility model:

```text
7A AlphaToPositionPrior
7B CurrentPositionStateEncoder
7C PositionGapProjector
7D CostToAdjustEstimator
7E RiskBudgetFitEvaluator
7F HorizonPositionResolver
7G PositionProjectionComposer
```

Physical code/tests use `7*` prefixes under the current ten-layer model surface.

### 7A - AlphaToPositionPrior

Converts final adjusted Layer 5 alpha into a raw target-position prior:

```text
alpha direction
alpha strength
expected residual return
alpha confidence
signal reliability
path quality
reversal/drawdown risk
alpha tradability
  -> raw target position prior
```

Diagnostic fields may include:

```text
7_raw_target_position_bias_score_<horizon>
7_raw_target_exposure_prior_score_<horizon>
7_alpha_position_conversion_score_<horizon>
```

### 7B - CurrentPositionStateEncoder

Encodes current and pending exposure state so Layer 7 can decide whether the account is already close to the target state, overexposed, underexposed, or directionally conflicted.

### 7C - PositionGapProjector

Computes the signed target-current gap using effective exposure:

```text
7_position_gap_score_<horizon>
= 7_target_exposure_score_<horizon>
- effective_current_exposure
```

The gap may be clipped to `[-1, 1]` for model-facing score output while diagnostics preserve the unclipped calculation if needed.

`7_position_gap_magnitude_score_<horizon>` is the normalized absolute gap. It describes distance from target state, not urgency or final action.

### 7D - CostToAdjustEstimator

Estimates the cost pressure of changing the current effective exposure toward the target exposure. The cost should be gap-aware:

```text
cost_to_adjust_position
~= estimated_adjustment_cost(abs(position_gap))
   / (abs(expected_position_utility) + epsilon)
```

The output is compressed to `[0, 1]`, where high is bad.

### 7E - RiskBudgetFitEvaluator

Evaluates whether the target exposure fits current portfolio/risk state. Kill-switch and drawdown gates may compress target exposure or force risk-budget fit to zero, but final action remains downstream.

### 7F - HorizonPositionResolver

Resolves conflicting per-horizon position projections. It should not simply average horizons when short and long horizon projections conflict.

Model-local or handoff summary fields may include:

```text
7_dominant_projection_horizon
7_horizon_conflict_state
7_resolved_target_exposure_score
7_resolved_position_gap_score
7_projection_resolution_confidence_score
7_horizon_resolution_reason_codes
```

These are Layer 7 handoff summary fields, not final actions.

### 7G - PositionProjectionComposer

Composes the final `position_projection_vector`: core per-horizon scores, handoff summary, diagnostics refs, range clipping, effective-exposure adjustment, cost/risk downgrades, horizon consistency checks, and reason-code attribution.

## V1 horizons

Layer 7 V1 uses the same synchronized horizons as Layers 5 and 6:

```text
10min
1h
1D
1W
```

`1D` means a rolling 24-hour natural-time horizon and `1W` means a rolling 7-calendar-day horizon. Equity and ETF labels observe tradable path inside those natural-time windows; crypto labels observe continuous path. Overlapping labels require purge/embargo controls.

## Core output contract

The V1 primary `position_projection_vector` exposes 10 core score families per horizon:

```text
7_target_position_bias_score_<horizon>
7_target_exposure_score_<horizon>
7_current_position_alignment_score_<horizon>
7_position_gap_score_<horizon>
7_position_gap_magnitude_score_<horizon>
7_expected_position_utility_score_<horizon>
7_cost_to_adjust_position_score_<horizon>
7_risk_budget_fit_score_<horizon>
7_position_state_stability_score_<horizon>
7_projection_confidence_score_<horizon>
```

Physical SQL column names must avoid unquoted numeric-leading identifiers unless the storage contract explicitly quotes them. These names are canonical registry/vector payload tokens and may live inside JSONB/vector payloads.

## Core field semantics

| Field family | Range | Directionality | High value means |
|---|---:|---|---|
| `7_target_position_bias_score_<horizon>` | `[-1, 1]` | signed | preferred target holding direction; positive = long exposure bias, negative = short exposure bias |
| `7_target_exposure_score_<horizon>` | `[-1, 1]` | signed exposure | normalized abstract target risk exposure, not shares/contracts/orders |
| `7_current_position_alignment_score_<horizon>` | `[0, 1]` | direction-neutral | current plus pending position is already close to the target state |
| `7_position_gap_score_<horizon>` | `[-1, 1]` | signed gap | target exposure minus effective current exposure |
| `7_position_gap_magnitude_score_<horizon>` | `[0, 1]` | direction-neutral | absolute normalized distance between target and effective current exposure |
| `7_expected_position_utility_score_<horizon>` | `[-1, 1]` | signed utility | expected risk-adjusted net utility of the projected target state after position-level friction/risk penalties |
| `7_cost_to_adjust_position_score_<horizon>` | `[0, 1]` | high-is-bad | relative cost pressure for closing the position gap |
| `7_risk_budget_fit_score_<horizon>` | `[0, 1]` | high-is-good | target exposure fits current risk budget and portfolio constraints |
| `7_position_state_stability_score_<horizon>` | `[0, 1]` | high-is-good | target holding state is stable across alpha, horizon, cost, risk, and pending-order uncertainty |
| `7_projection_confidence_score_<horizon>` | `[0, 1]` | high-is-good | Layer 7 confidence in the alpha-to-position mapping |

`7_target_position_bias_score_<horizon>` and `7_target_exposure_score_<horizon>` are deliberately separate. Bias says which way the position wants to lean; exposure says how large the normalized target holding state should be after risk/cost constraints.

Example:

```text
7_target_position_bias_score_1h = +0.85
7_target_exposure_score_1h = +0.25
```

This means the projection is clearly long-biased but only supports a small long exposure after constraints. It is not a buy instruction.

## Handoff summary fields

Layer 7 may expose a resolved summary for Layer 8 so underlying-action planning does not re-solve horizon conflicts:

```text
7_dominant_projection_horizon
7_horizon_conflict_state
7_resolved_target_exposure_score
7_resolved_position_gap_score
7_projection_resolution_confidence_score
7_horizon_resolution_reason_codes
```

These fields summarize the projected target holding state. They do not choose instrument, contract, order type, underlying action, or final execution.

## Diagnostics and explainability fields

Diagnostic fields may include:

```text
7_raw_target_position_bias_score_<horizon>
7_raw_target_exposure_prior_score_<horizon>
7_alpha_position_conversion_score_<horizon>
7_effective_current_exposure_score
7_pending_adjusted_exposure_score
7_cost_adjustment_reason_codes
7_risk_budget_reason_codes
7_projection_reason_codes
```

Diagnostics explain why Layer 7 compressed or changed the raw alpha-to-position prior. Downstream production logic should not hard-depend on diagnostics without reviewed promotion.

## No-position and aligned-position policy

No-position or aligned-position cases must not create arbitrary nulls in model-facing core fields.

If alpha exists but current plus pending exposure already matches the target exposure:

```text
7_current_position_alignment_score_<horizon> = high
7_position_gap_score_<horizon> = near 0
7_position_gap_magnitude_score_<horizon> = near 0
```

This does not mean hold as a final action; it means the current projected holding state is already aligned.

If risk budget is unavailable or kill-switch policy forces exposure compression:

```text
7_risk_budget_fit_score_<horizon> = low / 0
7_target_exposure_score_<horizon> compressed to the allowed range
reason codes include the policy gate
```

Final approval, forced close, cancel, or do-not-trade action remains downstream.

## Training and evaluation route

Layer 7 should avoid training only a single hindsight-best exposure target. Instead, prefer a candidate-exposure utility curve:

```text
Q(z_t, e) -> utility
```

Where:

```text
z_t = alpha_confidence_vector
    + current_position_state
    + pending_position_state
    + cost/risk context

e = candidate target exposure
```

Candidate exposure values may start as a reviewed discrete grid:

```text
-1.00, -0.75, -0.50, -0.25, 0.00, +0.25, +0.50, +0.75, +1.00
```

At inference time, Layer 7 selects the target exposure with the best point-in-time estimated utility after constraints. The selected target exposure remains a target holding state, not an order quantity.

## Labels and outcomes

Training/evaluation labels may include future outcomes, but inference features may not.

Evaluation labels can include:

```text
realized_position_utility_<horizon>
realized_target_exposure_utility_<horizon>
realized_position_gap_utility_<horizon>
realized_cost_to_adjust_position_<horizon>
realized_risk_budget_breach_<horizon>
realized_drawdown_under_projected_position_<horizon>
realized_turnover_penalty_<horizon>
current_position_hold_utility_<horizon>
flat_position_utility_<horizon>
target_position_vs_current_position_lift_<horizon>
candidate_exposure_utility_curve_<horizon>
target_exposure_regret_vs_best_candidate_<horizon>
```

Labels must be materialized only in training/evaluation datasets and must not be joined into `position_projection_vector` at inference time.

## Baselines and validation

Layer 7 should prove incremental value over:

1. current-position unchanged baseline;
2. flat-position baseline;
3. Layer 5 alpha-only exposure mapping;
4. fixed exposure by confidence baseline;
5. cost-blind position projection;
6. risk-budget-blind position projection;
7. simple horizon averaging baseline;
8. highest-confidence-horizon baseline;
9. full PositionProjectionModel.

Validation must separately check:

- utility: high `7_expected_position_utility_score_<horizon>` buckets realize better risk-adjusted net utility;
- alignment: high `7_current_position_alignment_score_<horizon>` reduces unnecessary turnover;
- cost: high `7_cost_to_adjust_position_score_<horizon>` identifies cases where changing exposure was not worthwhile;
- risk: high `7_risk_budget_fit_score_<horizon>` reduces risk-budget breaches and concentration blow-ups;
- gap: `7_position_gap_score_<horizon>` correctly represents target-current mismatch using effective exposure;
- stability: `7_position_state_stability_score_<horizon>` distinguishes durable target states from horizon/cost/risk-conflicted states;
- horizon resolution: resolved summaries improve over simple averaging or fixed-horizon baselines;
- leakage: all position, pending, cost, and risk inputs are point-in-time.

## Boundary rules and invariants

Layer 7 must keep these semantics separate:

```text
alpha confidence != target exposure
target position bias != buy/sell
target exposure != order quantity
position gap != execution instruction
position gap magnitude != urgency
cost to adjust position != no-trade action
risk budget fit != final approval
projection confidence != alpha confidence
position projection vector != final action
```

Layer 7 invariants:

1. `7_target_exposure_score_<horizon>` is abstract target risk exposure, not shares, contracts, or order quantity.
2. `7_position_gap_score_<horizon>` is the difference between target state and current/pending state, not an execution instruction.
3. Layer 7 does not output buy/sell/hold/open/close/reverse.
4. Layer 7 does not choose instrument, read option chains, or choose strike/DTE/Greeks.
5. Layer 7 uses only point-in-time current/pending/cost/risk state.
6. Layer 7 defaults to final adjusted Layer 5 alpha; base/unadjusted alpha is diagnostic-only.
7. Layer 7 output may be compressed by risk policy, but final approval and operation remain downstream.

## V1 implementation route

1. **V1.0 contract and boundary**: document `PositionProjectionModel`, `position_projection_vector`, inputs, outputs, handoff summary, diagnostics, and invariants. **Done.**
2. **V1.1 deterministic scaffold**: implement a transparent alpha-to-position projection before training a broad model. **Done for local fixture rows.**
3. **V1.2 evaluation labels**: add cost-aware position utility labels, candidate exposure utility curves, current-vs-flat-vs-target utility, risk-budget breach labels, and turnover penalty labels. **Offline label/leakage helpers exist.**
4. **V1.3 learned utility model**: train `Q(position_context, candidate_exposure) -> net utility` with chronological splits, purge/embargo, and no-leakage checks. **Pending later promotion work.**
5. **V1.4 horizon resolver**: implement resolved projection summary and prove it beats simple horizon averaging, fixed-horizon, and highest-confidence-horizon baselines. **Deterministic resolver exists; baseline proof remains later promotion work.**
