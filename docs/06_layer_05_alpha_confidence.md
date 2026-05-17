# Layer 05 — AlphaConfidenceModel

<!-- ACTIVE_LAYER_REVISION -->
Status: active architecture revision. Layer 5; current physical implementation surface is `src/models/model_05_alpha_confidence/`.

Active boundary: Layer 5 consumes the reviewed Layer 1/2/3 state stack plus Layer 4 `event_failure_risk_vector` when available and produces `alpha_confidence_vector` / base-alpha diagnostics. It does not consume arbitrary raw event evidence; only reviewed Layer 4 event-failure-risk conditioning is allowed upstream, while Layer 9 remains the residual event-risk governor.

Allowed outputs: horizon-aware alpha direction, strength, expected residual return, confidence, reliability, path quality, reversal risk, drawdown risk, and alpha tradability. Forbidden outputs: target exposure, position size, buy/sell/hold, option contract, order fields, broker/account mutation.

Supersedes older wording in this file that described EventRiskGovernor as Layer 5 before alpha. Any remaining legacy implementation references are physical-path notes only, not the conceptual stack order.
<!-- /ACTIVE_LAYER_REVISION -->


Status: accepted Layer 5 design route; deterministic V1 scaffold currently implemented in physical `src/models/model_05_alpha_confidence/`.

## Purpose

`AlphaConfidenceModel` is Layer 5. It consumes the reviewed Layer 1/2/3 state stack and calibration evidence to produce the base `alpha_confidence_vector`.

Layer 5 answers:

- Is there tradable alpha over `5min`, `15min`, `60min`, or `390min`?
- Is the alpha direction biased long, biased short, mixed, or neutral?
- How strong is the alpha, independent of direction?
- How reliable and calibrated is this judgment?
- Is the expected residual return actually target-specific, or mostly market/sector beta?
- Is the forward path likely to be tradeable, or likely to reverse/draw down first?
- Is the alpha good enough to hand to Layer 6 for position-projection work?

Layer 5 does **not** answer trading-intent, exposure, position-size, option-contract, order-routing, or execution questions. It must not emit buy/sell/hold, final action, target exposure, account-risk allocation, option symbol, strike, DTE, delta, order type, or broker mutation fields.

## Position and input chain

Layer 5 is the first model layer allowed to convert reviewed state/context plus reviewed event-failure-risk conditioning into horizon-aware alpha judgment. The accepted chain is:

```text
market_context_state
+ sector_context_state
+ target_context_state / target_state_vector
+ event_failure_risk_vector / reviewed event-failure conditioning
+ point-in-time quality and calibration evidence
  -> AlphaConfidenceModel
  -> alpha_confidence_vector
```

Layer 3 `3_target_direction_score_<window>` is signed current-state direction evidence, not alpha confidence. Layer 5 owns the calibrated alpha-confidence step. Reviewed strategy-failure event evidence belongs to Layer 4; residual/unreviewed event governance belongs to Layer 9.

## Two-tier output policy

Layer 5 deliberately keeps two surfaces separate:

1. **Base-alpha diagnostics**
   - built from Layer 1/2/3 state plus separately auditable Layer 4 event-failure conditioning when applicable;
   - used for research, debugging, audit, and calibration attribution;
   - not a trading action or exposure target.

2. **Default `alpha_confidence_vector`**
   - built from base alpha plus quality, calibration, path-risk, and point-in-time controls;
   - the only default Layer 6-facing Layer 5 output.

```text
Layer 1/2/3
+ reviewed Layer 4 event-failure conditioning when applicable
+ quality/calibration/path-risk controls
  -> alpha_confidence_vector
```

Layer 6 should consume the `alpha_confidence_vector` by default. Layer 9 event-adjusted risk guidance, if available, is applied later against the base trading guidance record rather than being a hard prerequisite here.

## Inputs

Production inference inputs must be point-in-time only:

```text
decision_time
available_time
tradeable_time
target_candidate_id
horizons
session_phase
market_context_state_ref
sector_context_state_ref
target_context_state_ref / target_state_vector_ref
state_version
model_version
quality/calibration refs visible by available_time
```

Training/evaluation inputs may include future outcomes as labels, but those labels must stay outside inference features.

### Input A - Layer 1 market context

Layer 5 may consume the reviewed `market_context_state`, including market direction, direction strength, trend quality, stability, risk stress, transition risk, breadth participation, correlation crowding, dispersion opportunity, liquidity pressure/support, coverage, and data quality.

Layer 5 uses these fields to decide whether the market background supports or overwhelms target-specific alpha.

### Input B - Layer 2 sector context

Layer 5 may consume the reviewed `sector_context_state`, including relative direction, trend quality/stability, transition risk, market-context support, breadth confirmation, dispersion/crowding, liquidity/tradability, state quality, coverage, data quality, and handoff state/bias/rank.

Layer 5 uses these fields to decide whether target alpha is sector-supported, sector-conflicted, or mostly sector beta.

### Input C - Layer 3 target state vector

Layer 3 is the primary state input. Layer 5 consumes reviewed target-state fields such as:

```text
3_target_direction_score_<window>
3_target_trend_quality_score_<window>
3_target_path_stability_score_<window>
3_target_noise_score_<window>
3_target_transition_risk_score_<window>
3_target_liquidity_tradability_score
3_context_direction_alignment_score_<window>
3_context_support_quality_score_<window>
3_tradability_score_<window>
3_state_quality_score
3_evidence_count
```

It may also use reviewed cross-state/residual features when available, such as target-vs-market residual direction, target-vs-sector residual direction, beta/correlation dependency, idiosyncratic residual state, and relative liquidity/tradability state.

Layer 5 may learn that positive or negative target-state evidence has predictive value, but it must not treat Layer 3 direction evidence as a trade instruction or final confidence value.

### Non-blocking Layer 9 event-risk context

Layer 9 event intelligence is not a required input for Layer 5 alpha-confidence generation. Reviewed `event_context_vector` / event-risk evidence may be referenced as diagnostics or later risk-governor context, but it must not be treated as a hard upstream prerequisite for base alpha.

Events may later enhance, weaken, contaminate, block, cap, or require review of the base guidance through the Layer 9 EventRiskGovernor boundary. Ordinary event evidence should not be folded into Layer 5 as duplicate state alpha.

### Input E - quality, calibration, and research memory

Layer 5 needs point-in-time reliability inputs such as:

```text
layer_1_quality_score
layer_2_quality_score
layer_3_quality_score
layer_4_quality_score
feature_coverage_score
data_quality_score
state_quality_score
layer_9_event_artifact_quality_score
state_neighborhood_sample_count
state_neighborhood_outcome_stability
model_ensemble_agreement_score
model_disagreement_score
out_of_distribution_score
historical_calibration_bucket_stats
walk_forward_reliability_stats
```

These fields do not create alpha by themselves. They influence confidence, reliability, and final tradability.

## Inputs explicitly excluded

Layer 5 must not use account, position, expression, or execution state:

```text
current_position_size
current_position_direction
current_PnL
unrealized_PnL
portfolio_risk_budget
account_drawdown
available_buying_power
recent_trade_result
buy/sell/hold labels
option_contract
strike
DTE
delta
final_action
execution_result
```

These belong to Layer 6/7/8/9 or training-label/evaluation surfaces, not Layer 5 inference.

## Internal structure

Layer 5 V1 uses six auditable submodules before any broad black-box confidence modeling:

```text
5A BaseStateAlphaEncoder
5B BaselineAdjustedAlphaDecomposer
5C EventRiskDiagnosticBridge
5D PathRiskEstimator
5E ConfidenceCalibrationLayer
5F AlphaVectorComposer
```

### 5A - BaseStateAlphaEncoder

Uses only Layer 1/2/3 state evidence to generate the base alpha judgment. It produces diagnostic `base_alpha_vector` fields such as:

```text
5_base_alpha_direction_score_<horizon>
5_base_alpha_strength_score_<horizon>
5_base_expected_return_score_<horizon>
5_base_path_quality_score_<horizon>
5_base_reversal_risk_score_<horizon>
5_base_drawdown_risk_score_<horizon>
5_base_alpha_tradability_score_<horizon>
```

These are not the default downstream contract. They explain what the state stack said before Layer 4 event-failure conditioning and later Layer 9 event-risk review are attributed.

### 5B - BaselineAdjustedAlphaDecomposer

Separates target alpha from market/sector beta. Diagnostic fields may include:

```text
5_market_adjusted_alpha_score_<horizon>
5_sector_adjusted_alpha_score_<horizon>
5_target_state_lift_score_<horizon>
5_idiosyncratic_alpha_score_<horizon>
5_beta_dependency_score_<horizon>
```

If beta dependency is high and target-state lift is low, Layer 5 should avoid claiming target-specific alpha.

### 5C - EventRiskDiagnosticBridge

Carries optional reviewed Layer 9 event-risk diagnostics for later governance without making event evidence a hard Layer 5 alpha input. Any event-driven block/cap/review/flatten candidate remains a Layer 9 EventRiskGovernor intervention, not a Layer 5 alpha override.

Diagnostic fields may include:

```text
5_event_direction_adjustment_score_<horizon>
5_event_strength_adjustment_score_<horizon>
5_event_confidence_adjustment_score_<horizon>
5_event_risk_adjustment_score_<horizon>
5_event_tradability_adjustment_score_<horizon>
5_event_override_mode_<horizon>
5_event_adjustment_reason_codes_<horizon>
```

### 5D - PathRiskEstimator

Estimates whether the alpha path is tradeable, not merely whether the endpoint is correct. It should model MFE, MAE, first-touch behavior, direction persistence, reversal, drawdown, noise, liquidity, and event-driven path contamination.

### 5E - ConfidenceCalibrationLayer

Calibrates confidence and reliability from point-in-time sample support, ensemble agreement/disagreement, OOD evidence, data quality, event uncertainty, walk-forward reliability, and confidence-bucket realized calibration.

Layer 5 alpha confidence fields use the Layer 5 semantic family in current physical code/SQL. `alpha_confidence_score_<horizon>` means current model belief. `signal_reliability_score_<horizon>` means similar-signal historical out-of-sample reliability. They are related but not interchangeable.

### 5F - AlphaVectorComposer

Composes base alpha, event adjustment, baseline adjustment, path risk, quality gates, and calibration into the final adjusted `alpha_confidence_vector`. It performs range clipping, horizon consistency checks, risk consistency checks, reason-code attribution, and quality downgrades.

## V1 horizons

Layer 5 V1 uses synchronized alpha-confidence horizons:

```text
5min
15min
60min
390min
```

`390min` means one regular US equity session-equivalent horizon measured in tradable minutes. Label builders must document whether a row resolves inside the same session or carries to the next regular-session close; overlapping labels require purge/embargo controls.

## Final adjusted output contract

The V1 Layer 5-facing output is exactly 9 core score families per horizon, for 36 final score tokens:

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

Physical SQL column names must avoid unquoted numeric-leading identifiers unless the storage contract explicitly quotes them. These names are canonical registry/vector payload tokens and may live inside JSONB/vector payloads.

## Core field semantics

| Field family | Range | Directionality | High value means |
|---|---:|---|---|
| `5_alpha_direction_score_<horizon>` | `[-1, 1]` | signed | positive = long alpha, negative = short alpha, near zero = mixed/neutral/no edge |
| `5_alpha_strength_score_<horizon>` | `[0, 1]` | direction-neutral | stronger absolute alpha magnitude, whether long or short |
| `5_expected_return_score_<horizon>` | `[-1, 1]` | signed | stronger standardized residual alpha expectation after market/sector baseline adjustment |
| `5_alpha_confidence_score_<horizon>` | `[0, 1]` | direction-neutral | model is more confident in the alpha judgment |
| `5_signal_reliability_score_<horizon>` | `[0, 1]` | direction-neutral | similar signals have been more stable out-of-sample |
| `5_path_quality_score_<horizon>` | `[0, 1]` | direction-conditioned | path is smoother, more persistent, and easier to trade |
| `5_reversal_risk_score_<horizon>` | `[0, 1]` | direction-conditioned | alpha direction is more likely to be interrupted/reversed; high-is-bad |
| `5_drawdown_risk_score_<horizon>` | `[0, 1]` | direction-conditioned | adverse excursion/MAE risk is higher; high-is-bad |
| `5_alpha_tradability_score_<horizon>` | `[0, 1]` | alpha-level | alpha is more suitable to hand to Layer 6 for position projection |

`5_alpha_tradability_score_<horizon>` is still not a trade instruction. It is only the Layer 5 judgment that the alpha is worth downstream position-projection mapping.

## No-edge and null policy

No-edge windows should not create arbitrary nulls in model-facing core fields.

Default no-edge policy:

```text
5_alpha_direction_score_<horizon> = 0
5_alpha_strength_score_<horizon> = 0
5_expected_return_score_<horizon> = 0
5_alpha_confidence_score_<horizon> = low/neutral according to calibration evidence
5_signal_reliability_score_<horizon> = low when sample support is insufficient
5_path_quality_score_<horizon> = neutral/baseline
5_reversal_risk_score_<horizon> = neutral/high when state/event risk is unclear
5_drawdown_risk_score_<horizon> = neutral/high when state/event risk is unclear
5_alpha_tradability_score_<horizon> = low
```

A zero direction estimate is not a hold instruction. Layer 6 projects target holding state and exposure after costs, risk budget, current/pending position state, and no-trade policy are reviewed.

## Labels and outcomes

Training/evaluation labels may include future outcomes, but inference features may not.

Evaluation labels can include:

```text
forward_return_<horizon>
market_adjusted_forward_return_<horizon>
sector_adjusted_forward_return_<horizon>
peer_adjusted_forward_return_<horizon>
idiosyncratic_residual_return_<horizon>
long_net_alpha_utility_<horizon>
short_net_alpha_utility_<horizon>
abs_residual_return_<horizon>
alpha_signal_to_noise_ratio_<horizon>
realized_max_favorable_excursion_<horizon>
realized_max_adverse_excursion_<horizon>
MFE_MAE_ratio_<horizon>
first_touch_profit_before_stop_<horizon>
path_smoothness_score_<horizon>
direction_flip_count_<horizon>
directional_persistence_realized_<horizon>
state_transition_occurred_<horizon>
confidence_bucket_realized_accuracy
similar_state_realized_hit_rate
walk_forward_signal_stability
out_of_sample_calibration_error
alpha_tradable_label_<horizon>
```

Labels must be materialized only in training/evaluation datasets and must not be joined into `alpha_confidence_vector` at inference time.

## Training route

Layer 5 should be trained in stages:

1. **Base alpha model**: train Layer 1/2/3-only base alpha outputs.
2. **Event-risk diagnostic bridge**: evaluate whether reviewed Layer 9 event-risk diagnostics explain base-alpha errors, event-window risk deterioration, or event-supported improvement without turning events into a hard upstream alpha input.
3. **Path/risk heads**: add MFE/MAE, first-touch, reversal, drawdown, liquidity, and event-risk labels.
4. **Calibration layer**: calibrate confidence, reliability, and tradability using walk-forward and out-of-sample buckets.

Do not train Layer 5 from in-sample Layer 1/2/3/4 model outputs. Upstream state vectors consumed by Layer 5 training must be generated with rolling/cross-fitted point-in-time discipline.

Overlapping horizons, especially `60min` and `390min`, require purge and embargo.

## Baselines and validation

Layer 5 should prove incremental value over:

1. no-alpha baseline;
2. market/sector context only;
3. Layer 3 direct target-state score baseline;
4. Layer 1/2/3 base alpha only;
5. Layer 9 event-risk context only;
6. Layer 1/2/3 plus simple event count;
7. Layer 1/2/3 plus full EventOverlay adjustment;
8. full Layer 5 with calibration.

Validation must separately check:

- direction: score buckets map monotonically to residual forward alpha;
- strength: stronger score buckets map to larger absolute residual alpha;
- confidence: confidence buckets are calibrated out-of-sample;
- reliability: reliable buckets generalize across years, sectors, and regimes;
- path: path quality/reversal/drawdown match MFE, MAE, first-touch, path smoothness, and transition outcomes;
- event adjustment: event-adjusted output improves over base only in visible point-in-time event contexts;
- tradability: high alpha-tradability rows improve path/risk/utility quality before Layer 6 costs and portfolio constraints;
- leakage: all feature rows obey `available_time <= decision_time`, and labels are isolated from inference features.

## Boundary rules

Keep these semantics separate:

```text
target direction evidence != alpha confidence
event direction bias != alpha confidence
base alpha != final adjusted alpha
alpha strength != alpha confidence
alpha confidence != signal reliability
expected return != target exposure
path quality != execution quality
risk != no-trade instruction
alpha tradability != trading signal
alpha confidence != planned underlying action
alpha confidence != option expression
alpha confidence != final action
```

Layer 5 must not:

- emit `buy`, `sell`, or `hold`;
- emit position size, target exposure, or account-risk allocation;
- choose option contract, strike, DTE, delta, or expression;
- mutate broker/account state;
- use account balance, buying power, PnL, open orders, holdings, or live execution constraints;
- use future returns, future event revisions, future option paths, or future fills as inference inputs.

## V1 implementation route

1. **V1.0 base alpha from Layer 1/2/3**: define labels, horizons, purge/embargo, and base/unadjusted diagnostics. **Done in deterministic scaffold for fixture rows.**
2. **V1.1 final 9-field `alpha_confidence_vector`**: implement direction, strength, expected return, confidence, reliability, path quality, reversal risk, drawdown risk, and alpha tradability. **Done in deterministic scaffold.**
3. **V1.2 EventRiskDiagnosticBridge**: keep optional `event_context_vector` references diagnostic only for later Layer 9 governance; do not make event evidence a hard Layer 5 alpha input. **Deterministic scaffold uses the current physical `model_05_alpha_confidence` package and `5_*` score-prefix hooks.**
4. **V1.3 baseline-adjusted diagnostics**: add market-adjusted, sector-adjusted, target-lift, idiosyncratic-alpha, and beta-dependency evidence. **Done in deterministic scaffold.**
5. **V1.4 calibration and promotion review**: persist walk-forward evidence and approve/defer promotion through the existing model-promotion governance path. **Offline label/leakage helpers exist; calibrated promotion evidence remains later work.**