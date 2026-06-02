# M01 - Market Regime / MarketRegimeModel

Status: accepted final learned broad-market conditional state estimator contract.

This file records the active direction-neutral market tradability/regime contract for Layer 1.

Layer 1 must be specified directly in its final learned-model contract form. It must not introduce a temporary learned contract, compatibility bridge, or learned-looking deterministic substitute. A final-contract Layer 1 artifact may move through evidence states such as `defined`, `trained_offline`, `replay_validated`, `shadow_candidate`, `promoted`, or `rejected`; those states are lifecycle evidence, not alternate architecture versions. Only a promoted artifact may affect production decisions.

## Learned Objective

Layer 1 learns a horizon-aware broad-market conditional state estimator:

```text
P_1(market_state_t+h | broad_market_context_t, input_frame, prediction_horizon)
  -> market_context_state
```

It estimates broad-market direction/state, trend persistence, volatility/stress, liquidity pressure/support, breadth, correlation/crowding, dispersion opportunity, transition risk, coverage, and data quality. It is not sector rotation, security selection, strategy selection, portfolio policy, position sizing, action guidance, option expression, or execution.

## Input

```text
trading_data.m01_market_regime_feature_generation
```

Layer 1 consumes broad-market and cross-asset evidence only. Sector/industry rotation, sector/industry ETF leadership, ETF holdings, selected securities, strategies, option contracts, portfolio actions, and future-return labels are excluded from production construction.

The upstream shared CSVs use `model_layer = layer_01_market_regime` to mark rows available to Layer 1 feature construction. Rows scoped to `layer_02_sector_context` belong to Layer 2 even when they live in the same static CSV asset.

## Timeframe contract

Layer 1 market context is horizon-aware. A current 1-minute market frame should not be trained to explain a 5-day market outcome, and a daily frame should not be treated as useful evidence for the next few minutes. Training and evaluation must pair each input frame with compatible future outcome horizons.

Accepted frame/horizon families:

```text
input_frame = 1min   -> prediction_horizon = 10min
input_frame = 10min  -> prediction_horizon = 1h
input_frame = 1h     -> prediction_horizon = 1D
input_frame = 1D     -> prediction_horizon = 1W
```

The target physical contract is one market-context row per `(available_time, input_frame, prediction_horizon, market_universe_ref)`. The same public state fields keep their compact `1_*` names inside each row; horizon and frame belong in row identity fields, not in duplicated column-name suffixes.

Future outcome metrics are labels and evaluation indicators only. They may calibrate whether a state output was useful for its paired horizon, but they must not enter same-row model construction.

## Allowed Learned Inputs

Layer 1 learned inputs are point-in-time broad-market and cross-asset evidence available at or before `available_time`:

- broad index, futures, rates, credit, volatility, breadth, liquidity, correlation, concentration, dispersion, and risk-appetite evidence;
- input frame, prediction horizon, market universe ref, feature coverage, freshness, and data-quality evidence;
- internal signal-group reductions from `m01_market_regime_feature_generation`;
- point-in-time missingness and no-data evidence when absence is explainable.

## Forbidden Learned Inputs

Layer 1 inference must exclude:

```text
sector/industry rotation
sector/industry ETF leadership
ETF holdings
selected securities
target candidate identity
strategy labels
portfolio actions
position state
option contracts
broker/account state
future returns
future volatility
future drawdown
future liquidity
future labels
```

Future outcome labels may be used only in training/evaluation datasets.

## Stage flow

```mermaid
flowchart LR
    source["trading_data source evidence<br/>point-in-time broad-market and cross-asset data"]
    feature["trading_data.m01_market_regime_feature_generation<br/>deterministic Layer 1 feature surface"]
    model["MarketRegimeModel<br/>Layer 1 model logic"]
    output["trading_model.m01_market_regime_model_generation<br/>primary market_context_state"]
    explain["trading_model.m01_market_regime_model_generation_explainability<br/>human-review state attribution"]
    diagnostics["trading_model.m01_market_regime_model_generation_diagnostics<br/>acceptance and gating evidence"]
    downstream["Layer 2+ conditioning context<br/>not sector/security selection"]

    source --> feature --> model
    model --> output --> downstream
    model --> explain
    model --> diagnostics
```

## Physical artifacts

```text
trading_model.m01_market_regime_model_generation
trading_model.m01_market_regime_model_generation_explainability
trading_model.m01_market_regime_model_generation_diagnostics
```

## `m01_market_regime_model_generation` - output

The primary output is the narrow downstream contract. It is keyed by `available_time` and describes whether the broad market / cross-asset background is clear, stable, low-transition-risk, liquid enough, and able to support downstream trading.

The accepted target key is:

```text
available_time
input_frame
prediction_horizon
market_universe_ref
```

Current fields:

```text
available_time
input_frame
prediction_horizon
market_universe_ref
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

`1_market_direction_score` records broad current direction sign only. It is not a long/short instruction and is not a quality score.

`1_market_trend_quality_score`, `1_market_stability_score`, `1_market_transition_risk_score`, `1_market_liquidity_pressure_score`, `1_market_liquidity_support_score`, `1_coverage_score`, and `1_data_quality_score` must remain separate. Market tradability should not collapse direction, trend clarity, risk stress, liquidity pressure, coverage, and data quality into one ambiguous readiness field.

## Missing-data tolerance

Layer 1 must tolerate missing upstream observations when the absence is point-in-time explainable, for example a symbol that was not yet listed in the requested historical month, a provider returning a reviewed no-data response, or a signal family lacking enough minimum history. Missing data should reduce `1_coverage_score` / `1_data_quality_score`, appear in diagnostics, and may block promotion through coverage gates; it should not by itself crash deterministic model construction or force the pipeline to invent synthetic bars.

The model may degrade confidence or withhold downstream unlocks when coverage is too low, but absence must stay explicit as evidence. Valid no-data evidence is different from provider failure, schema failure, leakage, or unreviewed stale data.

## `m01_market_regime_model_generation_explainability` - explainability

Explainability owns human-review detail that should not become a hard downstream dependency. It uses one row per `(available_time, factor_name)` with:

```text
available_time
factor_name
factor_value
explanation_payload_json
```

`factor_name` stores the public state-output name being explained. `explanation_payload_json` owns semantic contract metadata, source signal-group references, signal counts, evidence-role references, config references, and future accepted reason-code detail.

## `m01_market_regime_model_generation_diagnostics` - diagnostics

Diagnostics owns acceptance, monitoring, and gating evidence. It uses one row per `available_time` with:

```text
available_time
present_state_output_count
missing_state_output_count
data_quality_score
diagnostic_payload_json
```

`diagnostic_payload_json` owns missingness/freshness, minimum-history, standardization and z-score clipping checks, feature coverage, data-quality decomposition, chronological split/refit stability, downstream usefulness versus baselines, and no-future-leak checks.

## Labels And Evaluation

Training/evaluation labels may include future broad-market outcomes compatible with each frame/horizon pair:

```text
future_market_return_<horizon>
future_market_volatility_<horizon>
future_market_drawdown_<horizon>
future_liquidity_pressure_<horizon>
future_breadth_shift_<horizon>
future_correlation_crowding_<horizon>
future_transition_realization_<horizon>
downstream_calibration_lift_<horizon>
```

Labels must be materialized only in training/evaluation datasets and must not be joined into `market_context_state` at inference time. `1_coverage_score` and `1_data_quality_score` stay quality/gating evidence and are excluded from predictive-output coverage counts.

## Learned Artifact And Explainability

A promoted or promotion-candidate Layer 1 artifact must include model id, schema version, input-frame/prediction-horizon coverage, training and replay windows, feature schema hash, point-in-time source lineage, trained artifact payload, explainability refs, diagnostics refs, calibration evidence, missingness/coverage audits, chronological split evidence, and no-future-leak evidence.

Explainability must answer why the broad market state is directionally biased, stable/unstable, liquid/stressed, crowded/dispersive, transition-prone, and sufficiently covered. It must not explain why to select a sector, target, strategy, position, or action.

## Naming rule

Layer 1 model fields use compact `1_*` names in docs, model-facing payloads, and SQL physical columns. SQL writers should quote numeric-leading column names when needed rather than storing semantic aliases such as `layer01_*`.

Use `docs/21_vector_taxonomy.md` for cross-layer terminology. Layer 1 outputs `market_context_state`; it does not output a target vector, sector vector, alpha confidence, or position instruction.

Downstream consumers must select the market context that matches their decision horizon. Intraday entry logic should prefer short-frame contexts, risk and position logic may combine intraday and daily contexts, and swing/multi-day target work should use daily-frame contexts rather than a single undifferentiated market state.

## Layer acceptance

Layer 1 changes are acceptable when they:

- preserve the broad-market-only boundary and exclude sector/security/strategy/option/portfolio outcome leakage;
- preserve the frame/horizon pairing rule and prevent short-frame evidence from being evaluated against unrelated long-horizon labels;
- keep `trading_data.m01_market_regime_feature_generation` as the production input and `trading_model.m01_market_regime_model_generation` / `market_context_state` as the narrow downstream output;
- keep explainability and diagnostics as review/support artifacts rather than hard downstream dependencies;
- keep direction, direction strength, trend quality, stability, risk stress, transition risk, liquidity pressure/support, coverage, and data quality semantically separate;
- provide evidence-backed verification for generation, evaluation, smoke, and promotion-review paths when implementation changes;
- route new shared names, statuses, fields, or reason-code vocabularies through `trading-manager/scripts/` before cross-repository dependence.

Layer 1 validation must prove point-in-time construction, frame/horizon pairing, feature/model timestamp alignment, coverage and missingness handling, chronological split stability, baseline improvement over market-context-free downstream models, and no-future-leak checks. Runtime SQL smoke tests require an explicitly configured PostgreSQL target and should not run as default unit tests.
