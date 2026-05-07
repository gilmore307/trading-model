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
  -> TradingProjectionModel
  -> trading_signal_vector
```
