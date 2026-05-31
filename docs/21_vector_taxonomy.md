# Vector and State Taxonomy

Status: accepted naming discipline for the direction-neutral tradability design.

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

## Registered Abstract Terms

Some modeling words are ordinary trading words with narrower system-specific meanings. These must be registered as `term` rows in `trading-manager/scripts/registry/` before they become shared contract language.

Exposure-family terms use the registered meaning:

```text
normalized_risk_exposure
target_exposure
current_position_exposure
pending_exposure
effective_current_exposure
position_gap
```

Within this model stack, exposure means signed normalized risk exposure inside the accepted model/risk-budget scale. It is not shares, contracts, notional dollars, account percentage, broker order quantity, or a final action.

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
| `*_missingness_reason` | string / diagnostic payload field | Explainable absence such as not-yet-listed history, provider no-data, insufficient minimum history, stale feed, or schema failure. Diagnostic only unless a layer explicitly promotes it. |
| `*_tradability_score` | `[0, 1]` | Direction-neutral “how easy this state is to trade.” |

The central rule is:

```text
direction != quality != tradability != confidence != position size
```

## Layer 1 vocabulary

Input surface:

```text
trading_data.m01_market_regime_feature_generation
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
trading_data.m02_sector_context_feature_generation
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
context_etf_state
```

Use `context_etf_state` for the per-ETF Layer 2 output and reserve `cross_etf_summary` for global/group rotation summaries. The physical model surface remains `model_02_sector_context`.

Primary Layer 2 output should be narrow: signed ETF-context direction, direction-neutral trend/tradability state, separate handoff state and handoff bias, and row reliability. Explainability owns internal vectors; diagnostics owns gates.

Target routing has three accepted cases:

```text
layer1_market_etf_target -> market_context_state direct + cross_etf_summary support
layer2_context_etf_target -> own context_etf_state with self-context influence 1.0
ordinary_target -> target_context_profile weighted blend of context_etf_state rows
```

`context_etf_cross_section_row` is not a separate downstream output when its fields are already embedded in `context_etf_state`.

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

The Layer 3 conceptual output is `target_context_state`, aligned with `market_context_state` and Layer 2 `context_etf_state`. It consists of four inspectable blocks:

```text
market_state_features
sector_state_features
target_state_features
cross_state_features
```

Embedding and cluster outputs may exist as derived representation or diagnostics-supporting outputs, but they must not replace the four inspectable blocks as the primary contract.

## Layer 4 event-failure-risk vocabulary

Layer 4 model:

```text
EventFailureRiskModel
```

Conceptual output:

```text
event_failure_risk_vector
```

Future physical promoted artifact:

```text
trading_model.model_04_event_failure_risk
```

Primary model inputs are reviewed, point-in-time, and promotion-gated:

```text
market_context_state
context_etf_state
target_context_state
accepted event/strategy-failure evidence packet
agent review decision
manager-registered accepted scope
```

Core conceptual score families use the Layer 4 `4_event_*` namespace:

```text
4_event_strategy_failure_risk_score_<horizon>
4_event_entry_block_pressure_score_<horizon>
4_event_exposure_cap_pressure_score_<horizon>
4_event_strategy_disable_pressure_score_<horizon>
4_event_path_risk_amplifier_score_<horizon>
4_event_evidence_quality_score_<horizon>
4_event_applicability_confidence_score_<horizon>
```

Layer 4 is pre-alpha failure-risk conditioning only. It must not consume arbitrary raw events, discover new families, emit standalone directional alpha, choose actions/expression, or mutate broker/account state.

## Layer 5 alpha-confidence vocabulary

Layer 5 model:

```text
AlphaConfidenceModel
```

Conceptual output:

```text
alpha_confidence_vector
```

Physical promoted artifact remains:

```text
trading_model.model_05_alpha_confidence
```

Primary model inputs:

```text
market_context_state
context_etf_state
target_context_state / target_state_vector
event_failure_risk_vector              # Layer 4, when applicable
point-in-time quality/calibration evidence
```

The Layer 5 alpha-confidence vector is the calibrated directional opportunity layer after target state and reviewed event-failure conditioning. It is produced only through trained Layer 5 after-cost alpha artifacts:

```text
Layer 1/2/3 state stack
+ Layer 4 event_failure_risk_vector when applicable
+ quality/calibration/path-risk controls
  -> trained Layer 5 after-cost alpha artifacts
  -> AlphaConfidenceModel
  -> alpha_confidence_vector
```

Layer 5 score families use `5_*` alpha fields in physical code/SQL. The adjusted vector is alpha confidence only: not target exposure, not position sizing, not option expression, not execution, and not final action.

## Layer 6 dynamic-risk-policy vocabulary

Layer 6 model:

```text
DynamicRiskPolicyModel
```

Conceptual output:

```text
dynamic_risk_policy_state
```

Physical promoted artifact remains:

```text
trading_model.model_06_dynamic_risk_policy
```

Primary model inputs:

```text
market_context_state
systemic_event_risk_context
alpha_confidence_vector                 # Layer 5 final adjusted output
portfolio_exposure_context
portfolio_capacity_context
```

Layer 6 maps global and portfolio context into a dynamic risk/premium budget state. Physical score families use `6_*` prefixes. It is not buy/sell/hold, open/close/reverse, instrument selection, option-chain reading, strike/DTE/Greeks, execution, or final action.

## Layer 7 position-projection vocabulary

Layer 7 model:

```text
PositionProjectionModel
```

Conceptual output:

```text
position_projection_vector
```

Physical promoted artifact remains:

```text
trading_model.model_07_position_projection
```

Primary model inputs:

```text
alpha_confidence_vector                 # Layer 5 final adjusted output
dynamic_risk_policy_state               # Layer 6 risk budget
current_position_state
pending_position_state
position_level_friction_context
portfolio_exposure_context
point-in-time policy gates
```

Layer 7 maps alpha into target holding state and abstract exposure only. Physical score families use `7_*` prefixes. It is not buy/sell/hold, open/close/reverse, instrument selection, option-chain reading, strike/DTE/Greeks, execution, or final action.

## Layer 8 underlying-action plan semantics

Conceptual Layer 8 `underlying_action_plan` and `underlying_action_vector` values must keep these axes separate:

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

Physical underlying-action score families use `8_*` prefixes. Planned action types, resolved plan fields, reason codes, entry/target/stop prices, quantities, and Layer 9 handoff fields are plan payload fields, not broker-order fields.

## Layer 9 trading-guidance / option-expression semantics

Conceptual Layer 9 `trading_guidance_record`, `option_expression_plan`, and `expression_vector` values must keep these axes separate:

```text
underlying action plan != trading guidance approval
option expression != broker order
contract_ref != broker order id
selected_contract != send order
contract constraints != route / time-in-force
premium risk plan != account mutation
expression confidence != final approval
Layer 9 offline plan != live execution
```

Physical option-expression score families use `9_*` prefixes. Selected contract refs, contract constraints, premium-risk plan fields, and reason codes are plan payload fields, not broker-order fields.

## Layer 10 event-risk vocabulary

Layer 10 model:

```text
EventRiskGovernor / EventIntelligenceOverlay
```

Conceptual output:

```text
event_context_vector
event_risk_intervention
```

Physical promoted artifact remains:

```text
trading_model.model_10_event_risk_governor
```

Primary input source remains until a separate data/SQL migration:

```text
trading_data.m10_event_risk_governor_data_acquisition
```

Layer 10 is a point-in-time residual event-risk overlay whose canonical risk target is the Layer 8 direct-underlying thesis. Layer 9 trading-guidance / option-expression context is optional and absent for direct-underlying-only crypto routes:

```text
market_context_state
+ sector_context_state
+ target_context_state
+ event_failure_risk_vector
+ alpha_confidence_vector
+ position_projection_vector
+ underlying_action_plan / vector
+ optional trading_guidance_record / option_expression_plan / expression_vector
+ m10_event_risk_governor_data_acquisition
+ event_detail_artifacts
+ scope_mapping_metadata
+ sensitivity_metadata
  -> EventRiskGovernor
  -> event_risk_intervention / event_context_vector
```

Physical event-risk score families use `10_event_*` prefixes. Layer 10 may warn, explain, block/cap/reduce/flatten-review, maintain the observation pool, and propose Layer 4 promotion packets. It is not alpha confidence, not a trading signal, not position sizing, not expression selection, and not final action.

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

## Clean Flow

```text
trading_data.m01_market_regime_feature_generation
  -> MarketRegimeModel
  -> market_context_state

market_context_state
+ trading_data.m02_sector_context_feature_generation
  -> SectorContextModel
  -> context_etf_state

context_etf_state selected/watch
+ holdings/exposure
+ target-local point-in-time evidence
  -> Layer 3 preprocessing: anonymous target candidate builder
  -> anonymous_target_feature_vector

market_context_state
+ context_etf_state
+ anonymous_target_feature_vector
  -> TargetStateVectorModel
  -> target_context_state

target_context_state
+ reviewed event/strategy-failure evidence
  -> EventFailureRiskModel
  -> event_failure_risk_vector

target_context_state
+ event_failure_risk_vector
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

trading_guidance_record / option_expression_plan / expression_vector
+ residual event evidence
  -> EventRiskGovernor / EventIntelligenceOverlay
  -> event_risk_intervention

event-adjusted guidance / reviewed handoff
  -> downstream execution-owned broker/order lifecycle
```
