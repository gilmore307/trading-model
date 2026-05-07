# Layer 05 - AlphaConfidenceModel

Status: accepted Layer 5 design route; deterministic model implementation pending.

## Purpose

`AlphaConfidenceModel` is Layer 5. It converts the accepted target/context stack into an `alpha_confidence_vector` that estimates directional opportunity, expected value, risk, and uncertainty before any trading projection, option expression, position sizing, or execution decision.

Layer 5 answers:

- Given the current `target_context_state`, how confident is the model in long or short forward opportunity?
- How does `event_context_vector` adjust that confidence, expected value, and risk?
- Which horizons carry the strongest calibrated edge?
- Is the confidence well calibrated, uncertain, fragile, or unsupported by context?
- Does expected value remain positive after model-local risk and uncertainty penalties, before any account-specific sizing or expression choice?

Layer 5 does **not** answer trading-intent, exposure, position-size, option-contract, order-routing, or execution questions. It must not emit buy/sell/hold, final action, target exposure, account-risk allocation, option symbol, strike, DTE, delta, order type, or broker mutation fields.

## Position and input chain

Layer 5 is the first model layer allowed to convert direction-neutral target context and event context into calibrated directional alpha confidence:

```text
market_context_state
+ sector_context_state
+ target_context_state
+ event_context_vector
+ label/evaluation datasets for training only
  -> AlphaConfidenceModel
  -> alpha_confidence_vector
```

Layer 3 `3_target_direction_score_<window>` is signed current-state direction evidence, not alpha confidence. Layer 4 `4_event_direction_bias_score_<horizon>` is target-conditioned event bias, not alpha confidence. Layer 5 owns the calibrated confidence step that decides whether the combined context stack supports long or short opportunity.

## Inputs

Production inference inputs must be point-in-time only:

```text
available_time
tradeable_time
market_context_state_ref
sector_context_state_ref
target_context_state_ref
event_context_vector_ref
reviewed context-state payloads visible by available_time
reviewed event-context payload visible by available_time
model_config_ref
```

Training/evaluation inputs may include future outcomes as labels, but those labels must stay outside inference features.

### Input A - `target_context_state`

Layer 5 consumes the reviewed Layer 3 target state output, including:

```text
3_target_direction_score_<window>
3_target_direction_strength_score_<window>
3_target_trend_quality_score_<window>
3_target_path_stability_score_<window>
3_target_noise_score_<window>
3_target_transition_risk_score_<window>
3_target_state_persistence_score_<window>
3_target_exhaustion_risk_score_<window>
3_target_liquidity_tradability_score
3_context_direction_alignment_score_<window>
3_context_support_quality_score_<window>
3_tradability_score_<window>
```

Layer 5 may learn that strong positive or negative state evidence has predictive value, but it must not treat the Layer 3 sign as a trade instruction or final confidence value.

### Input B - `event_context_vector`

Layer 5 consumes the reviewed Layer 4 event context output, including event presence, timing, intensity, direction bias, context alignment, uncertainty, gap/reversal/liquidity/contagion risk, evidence quality, impact-scope strength, scope confidence, escalation risk, and target relevance.

Event fields adjust alpha confidence and expected value; they do not directly become actions. A high event risk can lower usable confidence even when target state direction is strong.

### Input C - upstream market/sector context

Layer 5 should retain refs to upstream states and may consume slim reviewed state values when needed for calibration:

```text
market_context_state_ref
sector_context_state_ref
target_context_state_ref
event_context_vector_ref
```

The canonical inference path should prefer reviewed state/context outputs over raw upstream feature shortcuts.

## Point-in-time and leakage rules

Layer 5 is a high-leakage-risk calibration layer. The primary visibility rule is:

```text
feature_visible := feature.available_time <= decision_available_time
```

Do not train or infer from:

- realized forward returns joined into inference rows;
- post-decision event revisions;
- future option-chain paths;
- future fills, PnL, open-order state, or account state;
- labels that were calculated using information unavailable at `available_time`.

Labels and realized paths are allowed only in training/evaluation datasets with explicit split, horizon, and availability controls.

## Internal model structure

Layer 5 V1 should be auditable and calibrated before broad black-box confidence modeling. The internal route is:

```text
5A ContextSignalAssembler
5B DirectionConfidenceCalibrator
5C EVRiskUncertaintyScorer
```

### 5A - ContextSignalAssembler

Consumes `target_context_state`, `event_context_vector`, and upstream state refs. It aligns windows/horizons and prepares the model-facing context stack.

Typical outputs:

```text
alpha_context_signal_vector
state_direction_evidence
state_tradability_evidence
event_adjustment_evidence
risk_penalty_evidence
quality_gate_evidence
```

### 5B - DirectionConfidenceCalibrator

Calibrates long/short direction confidence from context evidence and accepted labels. It must evaluate calibration, not only raw accuracy.

Typical outputs:

```text
raw_long_confidence
raw_short_confidence
signed_direction_confidence
confidence_strength
calibration_reliability
context_support
```

### 5C - EVRiskUncertaintyScorer

Combines calibrated confidence with expected return, risk, path, event, and uncertainty evidence into the accepted `alpha_confidence_vector` score families.

Typical scoring heads:

```text
direction_confidence_head
expected_return_head
expected_value_head
downside_risk_head
tail_risk_head
path_stability_head
uncertainty_head
context_support_head
event_adjustment_head
calibration_quality_head
```

## Output surface

Conceptual output:

```text
alpha_confidence_vector
```

Future physical promoted model-output surface:

```text
trading_model.model_05_alpha_confidence
```

The V1 output should be a point-in-time row keyed by decision context:

```text
available_time
tradeable_time
target_candidate_id
market_context_state_ref
sector_context_state_ref
target_context_state_ref
event_context_vector_ref
alpha_confidence_vector
alpha_confidence_vector_ref
score_payload
diagnostics_ref
```

`target_candidate_id` remains opaque. Raw ticker/company identity stays in audit/routing metadata outside fitting vectors.

## V1 horizons

Layer 5 V1 uses the same synchronized context horizons unless later evaluation proves a different prediction grid is needed:

```text
5min
15min
60min
390min
```

These are alpha-confidence prediction horizons, not trade-action variants and not option-expiration choices.

## V1 alpha-confidence vector score families

V1 uses horizon-aware scalar score families:

```text
5_alpha_direction_confidence_score_<horizon>
5_alpha_direction_strength_score_<horizon>
5_alpha_expected_return_score_<horizon>
5_alpha_expected_value_score_<horizon>
5_alpha_downside_risk_score_<horizon>
5_alpha_tail_risk_score_<horizon>
5_alpha_path_stability_score_<horizon>
5_alpha_uncertainty_score_<horizon>
5_alpha_context_support_score_<horizon>
5_alpha_event_adjustment_score_<horizon>
5_alpha_calibration_quality_score_<horizon>
```

V1-minimal may start with direction confidence, expected return/value, downside risk, uncertainty, context support, and calibration quality, but the accepted contract keeps path stability, tail risk, and event adjustment distinct because confidence, risk, and event-driven adjustment are separate semantics.

## Field semantics

| Field type | Range | High value means |
|---|---:|---|
| direction confidence | `[-1, 1]` | positive supports long opportunity; negative supports short opportunity; zero is no directional alpha confidence |
| direction strength | `[0, 1]` | stronger absolute confidence, regardless of long/short sign |
| expected return | signed normalized score | forward return expectation before final trading projection/sizing |
| expected value | signed normalized score | risk/uncertainty-adjusted alpha value before account-specific costs, expression, and sizing |
| downside risk | `[0, 1]` | adverse path or loss risk is higher; high-is-bad |
| tail risk | `[0, 1]` | extreme adverse outcome risk is higher; high-is-bad |
| path stability | `[0, 1]` | expected forward path is smoother/more tradable; high-is-good |
| uncertainty | `[0, 1]` | model confidence is less reliable; high-is-bad |
| context support | `[0, 1]` | market/sector/target/event context coherently supports the confidence estimate |
| event adjustment | `[-1, 1]` | event context shifts confidence positive/negative relative to no-event baseline |
| calibration quality | `[0, 1]` | confidence is historically calibrated and reliable for this context/horizon |

## No-edge and null policy

No-edge windows should not create arbitrary nulls in model-facing core fields.

Default no-edge policy:

```text
5_alpha_direction_confidence_score_<horizon> = 0
5_alpha_direction_strength_score_<horizon> = 0
5_alpha_expected_return_score_<horizon> = 0
5_alpha_expected_value_score_<horizon> = 0
5_alpha_downside_risk_score_<horizon> = neutral/baseline
5_alpha_tail_risk_score_<horizon> = neutral/baseline
5_alpha_path_stability_score_<horizon> = neutral/baseline
5_alpha_uncertainty_score_<horizon> = neutral/high when evidence is weak
5_alpha_context_support_score_<horizon> = low/neutral when context is weak
5_alpha_event_adjustment_score_<horizon> = 0
5_alpha_calibration_quality_score_<horizon> = low when calibration evidence is insufficient
```

A zero confidence estimate is not a hold instruction. Layer 6 decides offline trading intent/exposure after costs, risk budget, current/pending position state, and no-trade policy are reviewed.

## Labels and outcomes

Training/evaluation labels may include future outcomes, but inference features may not.

Evaluation labels can include:

```text
realized_signed_return_<horizon>
realized_direction_outcome_<horizon>
realized_excess_return_vs_market_<horizon>
realized_excess_return_vs_sector_<horizon>
realized_risk_adjusted_return_<horizon>
realized_max_favorable_excursion_<horizon>
realized_max_adverse_excursion_<horizon>
realized_path_efficiency_<horizon>
realized_path_volatility_<horizon>
realized_tail_loss_occurrence_<horizon>
realized_liquidity_degradation_<horizon>
realized_direction_flip_count_<horizon>
```

Labels must be materialized only in training/evaluation datasets and must not be joined into `alpha_confidence_vector` at inference time.

## Baselines and validation

Layer 5 should prove incremental value over:

1. market/sector context only;
2. Layer 3 target-direction baseline without event context;
3. Layer 4 event-adjusted baseline without calibrated alpha confidence;
4. simple momentum/reversion baseline;
5. no-event alpha baseline;
6. calibrated target+event full AlphaConfidenceModel.

Validation should check:

- calibration: predicted confidence buckets match realized long/short outcome frequencies;
- rank quality: higher confidence strength ranks produce better forward risk-adjusted outcomes;
- expected value: positive/negative EV scores correspond to realized excess return after risk penalties;
- risk: downside/tail/path scores correspond to MAE, tail loss, and path efficiency;
- event adjustment: event-adjusted confidence improves over no-event baselines only when events are visible point-in-time;
- stability: results survive walk-forward, market-regime, sector, and event/no-event splits;
- leakage: all feature rows obey `available_time <= decision_time` and label rows are isolated from inference features.

## Boundary rules

Keep these semantics separate:

```text
target direction evidence != alpha confidence
event direction bias != alpha confidence
confidence != expected value
expected value != target exposure
risk != no-trade instruction
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

1. **V1.0 label and horizon contract**: define point-in-time label materialization, split controls, and the 5min/15min/60min/390min prediction grid.
2. **V1.1 context signal assembler**: align Layer 3 target context and Layer 4 event context into the alpha-context signal vector without raw identity leakage.
3. **V1.2 confidence calibration**: train/evaluate signed direction confidence against market/sector/target/event baselines with reliability curves.
4. **V1.3 EV/risk/uncertainty scoring**: add expected return/value, downside/tail/path risk, uncertainty, event adjustment, and calibration quality heads.
5. **V1.4 evaluation and defer-or-approve review**: persist walk-forward evidence and approve/defer promotion through the existing model-promotion governance path.
