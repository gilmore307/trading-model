# Vector and State Taxonomy

Status: accepted naming discipline for the V2.2 direction-neutral tradability design.

This file owns the repository-wide vocabulary for `feature`, `vector`, `state`, `score`, `diagnostics`, `explainability`, and `label` terms. It exists because the Market/Sector/Target design has multiple nested evidence blocks, and not every block should be called a model or a state vector.

## Core vocabulary

| Term | Meaning | Contract rule |
|---|---|---|
| `feature_*` surface | Deterministic point-in-time input surface produced by `trading-data`. | Input to a model layer; not itself a model output. |
| `*_feature_vector` | Model-facing input feature collection assembled before or inside a model layer. | May be wide and block-structured; must exclude labels and forbidden identity fields. |
| `*_state` | Narrow current-state output of a model layer. | Stable downstream dependency surface. |
| `*_state_vector` | Block-structured model output state, used when a layer intentionally outputs a multi-block representation. | Reserved for Layer 3 target-state output unless a later layer explicitly accepts a state-vector contract. |
| `*_score` | Scalar field inside a state/vector/diagnostic block. | Do not call a scalar a vector. Do not let one score carry direction, quality, tradability, confidence, and position size at once. |
| `*_diagnostics` | Acceptance, monitoring, quality, leakage, freshness, coverage, and gating evidence. | May gate use, but is not the primary state contract unless promoted later. |
| `*_explainability` | Human-review attribution, evidence detail, reason-code expansion, and debug context. | Not a hard production dependency without explicit promotion. |
| `*_label` / `*_outcome` | Future-aware training/evaluation target. | Never enters inference features or model-facing state vectors. |

## Score-family discipline

Direction-neutral tradability requires separating these score meanings across layers:

| Score family | Range | Meaning |
|---|---|---|
| `*_direction_score` | `[-1, 1]` | Signed current-state long/short direction evidence. Negative is not bad by itself. |
| `*_direction_strength_score` | `[0, 1]` | Direction evidence magnitude when strength must be explicit separately from sign. |
| `*_trend_quality_score` | `[0, 1]` | Structural clarity of the trend state, independent of direction sign. |
| `*_stability_score` | `[0, 1]` | Persistence/smoothness and resistance to whipsaw. |
| `*_noise_score` | `[0, 1]` | Path chop, spikes, wick noise, and fake moves. Higher is worse. |
| `*_transition_risk_score` | `[0, 1]` | State-switch/decay/fragility risk. Higher is worse. |
| `*_liquidity_tradability_score` | `[0, 1]` | Spread, depth, capacity, borrow/shortability when applicable, and execution friendliness. |
| `*_coverage_score` | `[0, 1]` | Evidence completeness. Not opportunity. |
| `*_data_quality_score` | `[0, 1]` | Freshness, missingness, source quality, and reliability. Not opportunity. |
| `*_tradability_score` | `[0, 1]` | Direction-neutral “how easy this state is to trade.” |

The central rule is:

```text
direction != quality != tradability != confidence != position size
```

## Layer 1 vocabulary

Input surface:

```text
trading_data.feature_01_market_regime
```

Conceptual output state:

```text
market_context_state
```

Layer 1 should be described as broad market/cross-asset state, not as sector selection and not as a target vector.

The active market-tradability state separates:

```text
1_market_direction_score
1_market_direction_strength_score
1_market_trend_quality_score
1_market_stability_score
1_market_risk_stress_score
1_market_transition_risk_score
1_breadth_participation_score
1_correlation_crowding_score
1_dispersion_opportunity_score
1_market_liquidity_pressure_score
1_market_liquidity_support_score
1_coverage_score
1_data_quality_score
```

New downstream work should depend on these public state fields, not on implementation-local signal-group names.

## Layer 2 vocabulary

Input surfaces:

```text
market_context_state
trading_data.feature_02_sector_context
```

Internal/explainability vectors may include:

```text
2_sector_observed_behavior_vector
2_sector_attribute_vector
2_sector_conditional_behavior_vector
2_sector_trend_stability_vector
2_sector_tradability_vector
2_sector_risk_context_vector
2_sector_quality_diagnostics
```

Conceptual output state:

```text
sector_context_state
```

Primary Layer 2 output should be narrow: signed sector direction, direction-neutral trend/tradability state, separate handoff state and handoff bias, and row reliability. Explainability owns internal vectors; diagnostics owns gates.

`2_sector_handoff_state` and `2_sector_handoff_bias` must remain separate:

```text
selected | watch | blocked | insufficient_data
long_bias | short_bias | neutral | mixed
```

## Layer 3 preprocessing vocabulary

The anonymous target candidate builder is part of Layer 3 preprocessing. It is not a separate layer, not a separate model, and not a peer to `TargetStateVectorModel`.

Conceptual preprocessing row:

```text
anonymous_target_candidate[available_time, target_candidate_id]
```

Layer 3 preprocessing output/input-to-model vector:

```text
anonymous_target_feature_vector
```

`anonymous_target_feature_vector` is an input feature vector for Layer 3 target-state fitting. It is not a model output state vector.

Allowed model-facing preprocessing blocks:

```text
target_behavior_vector
target_liquidity_tradability_vector
target_structural_bucket_vector
sector_context_projection_vector
market_context_projection_vector
exposure_transmission_vector
event_risk_context_vector
cost_and_constraint_vector
candidate_quality_vector
```

Audit/routing metadata such as symbol references must stay outside this feature vector.

## Layer 3 model vocabulary

Layer 3 model:

```text
TargetStateVectorModel
```

Conceptual output:

```text
target_context_state
```

Physical promoted artifact:

```text
trading_model.model_03_target_state_vector
```

The Layer 3 conceptual output keeps the historical `TargetStateVectorModel` implementation name, but downstream prose should call the state payload `target_context_state` so it aligns with `market_context_state` and `sector_context_state`. It consists of four inspectable blocks:

```text
market_state_features
sector_state_features
target_state_features
cross_state_features
```

Embedding and cluster outputs may exist as derived representation or diagnostics-supporting outputs, but they must not replace the four inspectable blocks as the primary contract.

## Layer 4 event vocabulary

Layer 4 model:

```text
EventOverlayModel
```

Conceptual output:

```text
event_context_vector
```

Future physical promoted artifact:

```text
trading_model.model_04_event_overlay
```

Primary input source:

```text
trading_data.source_04_event_overlay
```

The Layer 4 event vector is a point-in-time overlay on the accepted state stack:

```text
market_context_state
+ sector_context_state
+ target_context_state
+ source_04_event_overlay
+ event_detail_artifacts
+ scope_mapping_metadata
+ sensitivity_metadata
  -> EventOverlayModel
  -> event_context_vector
```

It consists of auditable event encoding, context matching, and overlay scoring blocks:

```text
event_timing_context
event_scope_context
event_type_context
event_intensity_context
event_directional_context
event_risk_context
event_quality_context
event_impact_scope_context
```

Accepted V1 score-family horizons are `5min`, `15min`, `60min`, and `390min`. V1 separates core event risk/quality families from impact-scope families:

```text
4_event_presence_score_<horizon>
4_event_timing_proximity_score_<horizon>
4_event_intensity_score_<horizon>
4_event_direction_bias_score_<horizon>
4_event_context_alignment_score_<horizon>
4_event_uncertainty_score_<horizon>
4_event_gap_risk_score_<horizon>
4_event_reversal_risk_score_<horizon>
4_event_liquidity_disruption_score_<horizon>
4_event_contagion_risk_score_<horizon>
4_event_context_quality_score_<horizon>
4_event_market_impact_score_<horizon>
4_event_sector_impact_score_<horizon>
4_event_industry_impact_score_<horizon>
4_event_theme_factor_impact_score_<horizon>
4_event_peer_group_impact_score_<horizon>
4_event_symbol_impact_score_<horizon>
4_event_microstructure_impact_score_<horizon>
4_event_scope_confidence_score_<horizon>
4_event_scope_escalation_risk_score_<horizon>
4_event_target_relevance_score_<horizon>
```

`4_event_dominant_impact_scope_<horizon>` may exist as a model-local enum audit/debug field, but it is not a scalar score family.

It is event context only. It is not alpha confidence, not a trading signal, not position sizing, not expression selection, and not final action.

## Layer 5 alpha-confidence vocabulary

Layer 5 model:

```text
AlphaConfidenceModel
```

Conceptual output:

```text
alpha_confidence_vector
```

Future physical promoted artifact:

```text
trading_model.model_05_alpha_confidence
```

Primary model inputs:

```text
market_context_state
sector_context_state
target_context_state / target_state_vector
event_context_vector
point-in-time quality/calibration evidence
```

The Layer 5 alpha-confidence vector is the calibrated directional opportunity layer after target state and event correction:

```text
Layer 1/2/3 state stack
  -> base_alpha_vector                 # diagnostic / unadjusted

base_alpha_vector
+ event_context_vector
+ quality/calibration/path-risk controls
  -> AlphaConfidenceModel
  -> alpha_confidence_vector           # final adjusted output
```

Accepted V1 score-family horizons are `5min`, `15min`, `60min`, and `390min`. V1 exposes exactly 9 final adjusted score families per horizon:

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

Base/unadjusted `5_base_*` values are diagnostics for audit/research/event attribution, not the default Layer 6-facing contract. The adjusted vector is alpha confidence only: not target exposure, not position sizing, not option expression, not execution, and not final action.


## Layer 6 position-projection vocabulary

Layer 6 model:

```text
PositionProjectionModel
```

Conceptual output:

```text
position_projection_vector
```

Future physical promoted artifact:

```text
trading_model.model_06_position_projection
```

Primary model inputs:

```text
alpha_confidence_vector                 # Layer 5 final adjusted output
current_position_state
pending_position_state
position_level_friction_context
portfolio_exposure_context
risk_budget_context
point-in-time policy gates
```

The Layer 6 position-projection vector is the account/portfolio-state-aware target holding-state layer:

```text
alpha_confidence_vector
+ current_position_state
+ pending_position_state
+ position-level friction context
+ risk-budget / portfolio exposure context
  -> PositionProjectionModel
  -> position_projection_vector
```

Accepted V1 score-family horizons are `5min`, `15min`, `60min`, and `390min`. V1 exposes exactly 10 core score families per horizon:

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

Layer 6 may also expose handoff summary fields for Layer 7:

```text
6_dominant_projection_horizon
6_horizon_conflict_state
6_resolved_target_exposure_score
6_resolved_position_gap_score
6_projection_resolution_confidence_score
6_horizon_resolution_reason_codes
```

`6_target_exposure_score_<horizon>` is abstract normalized risk exposure, not shares/contracts/order quantity. `6_position_gap_score_<horizon>` is target exposure minus effective current exposure, where effective current exposure includes pending exposure adjusted by fill probability. It is not an execution instruction.

Layer 6 is position projection only: not buy/sell/hold, not open/close/reverse, not instrument selection, not option-chain reading, not strike/DTE/Greeks, not execution, and not final action.

## Layer 7 underlying-action plan semantics

Layer 7 `underlying_action_plan` and `underlying_action_vector` values must keep these axes separate:

```text
alpha confidence != planned underlying action
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

Accepted Layer 7 score families use the `7_` prefix and `<horizon>` suffix for horizon-aware families. Planned action types, resolved plan fields, reason codes, entry/target/stop prices, quantities, and Layer 8 handoff fields are plan payload fields, not broker-order fields.

Core Layer 7 score families:

- `7_underlying_trade_eligibility_score_<horizon>` — `[0, 1]`, high-is-good direct-underlying trade eligibility.
- `7_underlying_action_direction_score_<horizon>` — `[-1, 1]`, signed planned direct-underlying side; positive long-side, negative short-side, near zero maintain/no-trade.
- `7_underlying_trade_intensity_score_<horizon>` — `[0, 1]`, high-is-more planned adjustment intensity after confidence/risk/cost compression.
- `7_underlying_entry_quality_score_<horizon>` — `[0, 1]`, high-is-good entry quality for the plan.
- `7_underlying_expected_return_score_<horizon>` — `[-1, 1]`, signed favorable direct-underlying return quality.
- `7_underlying_adverse_risk_score_<horizon>` — `[0, 1]`, high-is-bad adverse move / stop-risk pressure.
- `7_underlying_reward_risk_score_<horizon>` — `[0, 1]`, high-is-good reward/risk quality.
- `7_underlying_liquidity_fit_score_<horizon>` — `[0, 1]`, high-is-good direct-underlying liquidity/spread fit.
- `7_underlying_holding_time_fit_score_<horizon>` — `[0, 1]`, high-is-good compatibility between planned holding time and the signal/projection horizon.
- `7_underlying_action_confidence_score_<horizon>` — `[0, 1]`, calibrated confidence in the offline direct-underlying action thesis.

Resolved Layer 7 fields such as `7_resolved_underlying_action_type`, `7_resolved_action_side`, `7_resolved_dominant_horizon`, and `7_resolved_reason_codes` summarize the chosen plan for Layer 8 and execution-side review. They do not send orders.

## Layer 8 option-expression semantics

Layer 8 `option_expression_plan` and `expression_vector` values must keep these axes separate:

```text
underlying action plan != option expression
option expression != broker order
contract_ref != broker order id
selected_contract != send order
contract constraints != route / time-in-force
premium risk plan != account mutation
expression confidence != final approval
Layer 8 offline plan != live execution
```

Accepted Layer 8 score families use the `8_` prefix and `<horizon>` suffix for horizon-aware scalar scores. Selected contract refs, contract constraints, premium-risk plan fields, and reason codes are plan payload fields, not broker-order fields.

Core Layer 8 score families:

- `8_option_expression_eligibility_score_<horizon>` — `[0, 1]`, high-is-good option-expression admissibility.
- `8_option_expression_direction_score_<horizon>` — `[-1, 1]`, signed expression direction; positive call-side/bullish, negative put-side/bearish, near zero no-option expression.
- `8_option_contract_fit_score_<horizon>` — `[0, 1]`, high-is-good selected contract fit.
- `8_option_liquidity_fit_score_<horizon>` — `[0, 1]`, high-is-good option spread/volume/open-interest fit.
- `8_option_iv_fit_score_<horizon>` — `[0, 1]`, high-is-good IV/IV-rank fit.
- `8_option_greek_fit_score_<horizon>` — `[0, 1]`, high-is-good delta/Greek fit.
- `8_option_reward_risk_score_<horizon>` — `[0, 1]`, high-is-good premium reward/risk quality.
- `8_option_theta_risk_score_<horizon>` — `[0, 1]`, high-is-bad theta-decay pressure.
- `8_option_fill_quality_score_<horizon>` — `[0, 1]`, high-is-good conservative fill-quality estimate.
- `8_option_expression_confidence_score_<horizon>` — `[0, 1]`, calibrated confidence in the offline option-expression plan.

Resolved Layer 8 fields such as `8_resolved_expression_type`, `8_resolved_option_right`, `8_resolved_dominant_horizon`, `8_resolved_selected_contract_ref`, `8_resolved_contract_fit_score`, `8_resolved_no_option_reason_codes`, and `8_resolved_reason_codes` summarize the selected expression and do not send orders.

## Label boundary

Layer 3 labels/outcomes may include:

```text
signed_forward_return_distribution
forward_path_risk
directional_persistence
reversion_pressure
liquidity_tradability_outcome
state_transition
```

They are training/evaluation-only and must not be joined into:

```text
anonymous_target_feature_vector
target_context_state
```

## Clean V2.2 flow

```text
trading_data.feature_01_market_regime
  -> MarketRegimeModel
  -> market_context_state

market_context_state
+ trading_data.feature_02_sector_context
  -> SectorContextModel
  -> sector_context_state

sector_context_state selected/watch
+ holdings/exposure
+ target-local point-in-time evidence
  -> Layer 3 preprocessing: anonymous target candidate builder
  -> anonymous_target_feature_vector

market_context_state
+ sector_context_state
+ anonymous_target_feature_vector
  -> TargetStateVectorModel
  -> target_context_state

target_context_state
+ source_04_event_overlay evidence
  -> EventOverlayModel
  -> event_context_vector

target_context_state
+ event_context_vector
  -> AlphaConfidenceModel
  -> alpha_confidence_vector

alpha_confidence_vector
+ current/pending position context
+ risk/cost context
  -> PositionProjectionModel
  -> position_projection_vector

position_projection_vector
+ underlying quote/liquidity/risk-policy context
  -> UnderlyingActionModel
  -> underlying_action_plan / underlying_action_vector

underlying_action_plan / underlying_action_vector
+ option_chain_snapshot / option candidate context
  -> OptionExpressionModel
  -> option_expression_plan / expression_vector

option_expression_plan / expression_vector
  -> downstream execution-owned broker/order lifecycle
```
