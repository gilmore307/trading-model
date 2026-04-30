# Decision


## D001 - Market-state discovery is market-only

Date: 2026-04-25

### Context

The trading platform needs `trading-model` to have a clear owner boundary before implementation begins.

### Decision

State discovery inputs must be market/data-source features only; strategy performance is excluded until after state tables exist.

### Rationale

A narrow component boundary prevents hidden coupling and keeps cross-repository work reviewable.

### Consequences

- Implementation work must stay inside the accepted component role.
- Shared names and contracts must route through `trading-main`.
- Generated outputs and secrets must stay out of Git.


## D002 - Model research is offline

Date: 2026-04-25

### Context

The trading platform needs `trading-model` to have a clear owner boundary before implementation begins.

### Decision

This repository produces research artifacts and verdicts, not live trading decisions or order placement.

### Rationale

A narrow component boundary prevents hidden coupling and keeps cross-repository work reviewable.

### Consequences

- Implementation work must stay inside the accepted component role.
- Shared names and contracts must route through `trading-main`.
- Generated outputs and secrets must stay out of Git.


## D003 - Generated model artifacts stay out of Git

Date: 2026-04-25

### Context

The trading platform needs `trading-model` to have a clear owner boundary before implementation begins.

### Decision

State tables, trained outputs, model artifacts, and research runs are runtime artifacts unless accepted as tiny fixtures.

### Rationale

A narrow component boundary prevents hidden coupling and keeps cross-repository work reviewable.

### Consequences

- Implementation work must stay inside the accepted component role.
- Shared names and contracts must route through `trading-main`.
- Generated outputs and secrets must stay out of Git.

## D004 - Seven-layer offline modeling architecture supersedes market-state-only repository purpose

Date: 2026-04-27

### Context

The trading system data-source layer is now considered sufficiently complete for v1, and the next phase is to clarify model requirements. The prior `trading-model` boundary treated the repository primarily as market-state/regime research. Chentong explicitly replaced that old intent and accepted the current seven-layer architecture as the new basis.

### Decision

`trading-model` is the offline modeling home for the seven-layer trading decision system:

1. `MarketRegimeModel` (`market_regime_model`);
2. `SecuritySelectionModel` (`security_selection_model`);
3. `StrategySelectionModel` (`strategy_selection_model`);
4. `TradeQualityModel` (`trade_quality_model`);
5. `OptionExpressionModel` (`option_expression_model`);
6. `EventOverlayModel` (`event_overlay_model`);
7. `PortfolioRiskModel` (`portfolio_risk_model`).

Layer 6 is an overlay that can affect all earlier layers and the risk gate. Layer 7 is the final offline risk/execution gate, but live order placement remains outside this repository.

### Rationale

The model requirements determine cleaning, feature shape, event projection, bundle composition, and decision records. Keeping the full modeling stack in view prevents the data layer from hardening premature schemas and prevents Layer 1 from being designed as an isolated regime-labeling exercise.

### Consequences

- Earlier market-state-only wording is superseded except for the still-valid principle that Layer 1 regime discovery itself must not use strategy performance as an input.
- Phase 1 should still start with point-in-time market-state/regime modeling, but as Layer 1 of the full stack.
- Layers 2-7 may be implemented in phases inside `trading-model` unless a later decision splits ownership.
- Raw acquisition remains in `trading-data`; global shared contracts still route through `trading-main`; live/paper order placement remains outside `trading-model`.
- All layers must obey point-in-time validation and avoid event/news/label leakage.

## D005 - Canonical seven-layer model names

Date: 2026-04-27

### Context

After accepting the seven-layer architecture, the model layers need stable names before data organization, schemas, decision records, code packages, and registry proposals are finalized.

### Decision

Use the following canonical model names and stable ids:

| Layer | Model class | Stable id | Chinese name |
|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_regime_model` | 市场状态模型 |
| 2 | `SecuritySelectionModel` | `security_selection_model` | 标的选择模型 |
| 3 | `StrategySelectionModel` | `strategy_selection_model` | 策略选择模型 |
| 4 | `TradeQualityModel` | `trade_quality_model` | 交易质量模型 |
| 5 | `OptionExpressionModel` | `option_expression_model` | 期权表达模型 |
| 6 | `EventOverlayModel` | `event_overlay_model` | 事件覆盖模型 |
| 7 | `PortfolioRiskModel` | `portfolio_risk_model` | 组合风控模型 |

Layer 6 remains an overlay. Layer 7 may model execution-gate logic, but it must not be called `ExecutionModel` because live/paper order placement is outside `trading-model`.

### Rationale

Stable names prevent schema drift and keep future data organization, decision records, artifacts, code modules, and registry rows aligned.

### Consequences

- Docs, code, artifact metadata, and registry proposals should use these names unless a later decision renames them.
- Machine-facing paths/configs should prefer the stable ids.
- The canonical naming table in `docs/07_system_model_architecture_rfc.md` is the working reference until promoted into `trading-main` registry/contracts.

## D006 - SecuritySelectionModel bridges market regime to tradable symbols

Date: 2026-04-28

### Context

ETF holdings are not primarily a `MarketRegimeModel` input. Their key role is to transmit sector/style strength from ETF baskets into individual tradable stock candidates. The prior architecture jumped from market regime directly to strategy selection, which skipped the question of which symbols deserve strategy evaluation under the current regime.

### Decision

Add `SecuritySelectionModel` (`security_selection_model`) as Layer 2 between `MarketRegimeModel` and `StrategySelectionModel`.

`SecuritySelectionModel` owns target/security selection and universe construction. It uses market/sector/style context, ETF holdings exposures, full-market scans, individual stock relative strength, liquidity, optionability, and event exclusions to produce long, short, watch, and excluded candidate pools.

### Rationale

Different market regimes require different selection styles. Risk-on regimes may prefer high-relative-strength core holdings of strong ETFs; risk-off regimes may prefer defensive/low-volatility names or ETFs; rotation regimes may prefer newly strengthening holdings or laggards catching up. This is a distinct modeling problem from choosing strategy family or signal entry quality.

### Consequences

- `MarketRegimeModel` should output sector/style scores useful for security selection.
- `etf_holding_snapshot` becomes an important upstream data kind for Layer 2.
- A derived point-in-time `stock_etf_exposure` table should be designed, either model-local first or registered through `trading-main` if cross-repository use is needed.
- `StrategySelectionModel` consumes selected candidate pools instead of scanning the whole universe directly.
- Event and optionability exclusions can remove symbols before strategy evaluation.

## D007 - OptionExpressionModel V1 is single-leg long options only

Date: 2026-04-28

### Context

`OptionExpressionModel` selects the option contract or expression after signal quality and expected underlying move are known. Multi-leg structures introduce materially more complexity in pricing, margin, fill simulation, slippage, exit management, and risk controls.

### Decision

V1 `OptionExpressionModel` supports only simple single-leg option expressions:

- long call;
- long put.

Stock/ETF direct expression may remain a comparison or fallback, but V1 option expression must not choose debit spreads, calendars, diagonals, straddles, strangles, condors, butterflies, ratio spreads, or naked short options.

### Rationale

Single-leg long options are sufficient for the first option-expression research slice and keep modeling, backtesting, and execution assumptions auditable. Multi-leg option structures should wait until option-chain snapshot quality, conservative fill logic, slippage modeling, and exit lifecycle handling are proven.

### Consequences

- `OptionExpressionModel` V1 scoring ranks eligible calls/puts, not combinations of legs.
- Required inputs remain option chain snapshot, bid/ask, volume/open interest, DTE, IV, Greeks, liquidity, and previous model outputs.
- Multi-leg structures are explicitly deferred and should not appear in V1 decision records except as rejected/deferred capabilities.

## D008 - MarketRegimeModel V1 outputs a continuous market-state vector

Date: 2026-04-29
Status: Accepted

### Context

Layer 1 initially discussed unsupervised clustering, state ids, state probabilities, and human-readable regime names. Chentong clarified that hard states are unlikely to directly help later security selection or strategy selection because they are coarse, unstable after refits, and require another lookup layer to recover the underlying market conditions.

The useful downstream information is the concrete market-condition vector: trend, volatility stress, correlation stress, credit/rate/dollar/commodity pressure, sector rotation, breadth, risk appetite, and transition pressure.

### Decision

`MarketRegimeModel` V1 should not require clustering, HMM state assignment, hard `state_id`, `state_probability_*`, or pre-assigned human-readable labels.

The primary V1 output is a continuous point-in-time market-state vector in `trading_model.model_01_market_regime`, keyed by `available_time`.

The model should remain unsupervised in the sense that it does not train on pre-assigned market labels. It may use rolling/expanding standardization and feature-block factor/score extraction from `trading_data.feature_01_market_regime`.

### Consequences

- Discrete state/cluster artifacts are deferred and optional research diagnostics, not the main downstream contract.
- Layer 2/3 should consume continuous market-condition factors/scores rather than hard regime labels.
- Future-return labels may be used for evaluation only, not for constructing Layer 1 model outputs.
- The first implementation slice should focus on stable, interpretable, point-in-time factor/score generation before adding clustering or visualization branches.

## D009 - MarketRegimeModel V1 implementation slice

Date: 2026-04-29
Status: Accepted

### Context

After deciding that V1 should use a continuous market-state vector rather than clusters, the first implementation needs a small deterministic model-output slice that can be tested without provider calls, generated artifacts, or durable database mutation.

### Decision

Implement `model_01_market_regime` as an importable generator plus SQL runner:

- `src/model_outputs/model_01_market_regime/generator.py` owns point-in-time rolling standardization and factor generation.
- `scripts/generate_model_01_market_regime.py` reads `trading_data.feature_01_market_regime` and upserts `trading_model.model_01_market_regime`.
- Unit tests use in-memory fixture rows and fake cursors only.

The first factor set is:

- `trend_factor`
- `volatility_stress_factor`
- `correlation_stress_factor`
- `credit_stress_factor`
- `rate_pressure_factor`
- `dollar_pressure_factor`
- `commodity_pressure_factor`
- `sector_rotation_factor`
- `breadth_factor`
- `risk_appetite_factor`
- `transition_pressure`
- `data_quality_score`

Rows are keyed by `available_time`. If the upstream derived row has only `snapshot_time`, the model maps that timestamp to `available_time`.

### Consequences

- The implementation remains unsupervised and does not emit `state_id`, `state_probability_*`, or human-readable regime names.
- Rolling standardization uses prior rows only; current/future rows do not fit the current score.
- The factor formulas are V1 and intentionally reviewable; later evidence may revise exact signal membership or signs without changing the table role.
- Control-plane completion receipts and ready-signal files remain deferred until `trading-main` control-plane integration.

## D010 - MarketRegimeModel factor specs live in config

Date: 2026-04-29
Status: Accepted

### Context

The first implementation placed factor membership, signal direction, and reducer choice in Python code. That made the V1 state-vector construction harder to review and harder to adjust as the derived feature surface changes.

### Decision

Move `MarketRegimeModel` V1 factor definitions into `src/model_outputs/model_01_market_regime/config/factor_specs.toml`.

The TOML config owns:

- factor names;
- exact source columns or symbol/suffix expansions;
- signal direction (`1` or `-1`);
- reducer choice (`bounded_mean` or `bounded_abs_mean`).

The Python generator owns only config validation, point-in-time rolling standardization, reducer execution, transition-pressure calculation, data-quality calculation, and row shaping.

### Consequences

- Changing factor membership/signs/reducers no longer requires editing generator execution code.
- Config changes still require tests and review because they can change output semantics.
- Adding a new factor column still requires checking the SQL output contract and registry/docs implications.

## D011 - Stabilize MarketRegimeModel rolling factor construction

Date: 2026-04-29
Status: Accepted

### Context

The first V1 state-vector generator used a very small default `min_history = 3`, no explicit standard-deviation floor, no pre-reducer z-score clipping, and flat aggregation for broad trend signals. Chentong flagged that this would make early z-scores unstable, allow near-zero standard deviations to explode signal values, and make factor weighting harder to reason about as signal groups evolve.

### Decision

Stabilize factor construction through `config/factor_specs.toml`:

- default `min_history = 20`;
- group-level minimum-history overrides for more fragile feature types, including longer histories for correlation, volatility, and low-frequency/daily-style features;
- `std_floor = 1e-8` so near-constant signal history produces a neutral z-score instead of an explosive value;
- `z_clip = 5.0` before direction adjustment and reducer aggregation;
- `min_signal_coverage = 0.5` so factors remain `null` until enough configured signals have usable point-in-time z-scores;
- `data_quality_score` is based on eligible signal coverage, not merely raw non-null column presence;
- `trend_factor` uses `bucketed_mean`, first averaging trend signals by ETF/symbol bucket and then reducing across ETF buckets.

Clarify semantics:

- `commodity_pressure_factor` means commodity-related assets are becoming a dominant market driver; it is not automatically bearish.
- `rate_pressure_factor` means long-duration bonds are weakening versus short-duration bonds; safe-haven bond strength may become a separate factor later.

### Consequences

- Early rows produce `null` factors rather than unstable pseudo-signals.
- Low-variance feature histories no longer create extreme z-scores.
- Single outlier z-scores are clipped before they can dominate group means.
- Trend factor weighting is more robust if future ETF signal sets become uneven.
- Future model review should consider splitting commodity and rate factors if downstream interpretation needs separate inflation, safe-haven, and duration-shock dimensions.

## D012 - Manager-facing model data requests use required data windows only

Date: 2026-04-29
Status: Accepted

### Context

`MarketRegimeModel` evaluation needs train/validation/test windows and future-label horizons such as 1D, 5D, and 20D. Those details are model-evaluation semantics, not manager orchestration semantics. The control plane should coordinate production of source/feature data, but it should not need to understand how the model will use that data to construct labels or splits.

### Decision

Use the simple data-window request shape for control-plane-facing model data requests.

A control-plane-facing request should specify the raw data coverage needed:

- `request_id`
- `model_id`
- `purpose`
- `required_data_start_time`
- `required_data_end_time`
- `required_source_key`
- `required_derived_key`
- `requested_at`
- `request_status`
- optional `request_payload_json` for model-local opaque details

Do not put `label_horizons` into the control-plane-facing request contract. Label horizons, target symbols, split windows, and evaluation rules belong in model-owned evaluation config/run tables.

When future labels need data past the evaluation end time, the model planner should extend `required_data_end_time` before sending the request. For example, if the model wants to evaluate through 2025-12-31 with a 20D future label, the control-plane-facing request may ask for source/feature data through roughly late January 2026.

### Consequences

- The `trading-main` control plane only needs to prepare data coverage; it does not need model-label semantics.
- `trading-model` remains responsible for interpreting prepared data into train/validation/test splits and labels.
- Request field names should use `required_data_start_time` / `required_data_end_time`, not `dataset_start_time` / `dataset_end_time`, to avoid confusing manager data coverage with model dataset/evaluation windows.

## D013 - Use generic model governance table names

Date: 2026-04-29
Status: Accepted

### Context

Dataset requests, dataset snapshots, train/validation/test splits, evaluation labels, evaluation runs, and evaluation metrics are not unique to `MarketRegimeModel`. The same governance concepts will be needed by later model layers such as `SecuritySelectionModel`, `StrategySelectionModel`, and `TradeQualityModel`.

Registering layer-specific table names would duplicate the same schema shape across model layers. Registering every concrete column now would also prematurely freeze an evaluation schema before implementation validates it.

### Decision

Use generic `trading_model` governance table names for cross-layer model evaluation and dataset governance:

- `model_dataset_request`
- `model_dataset_snapshot`
- `model_dataset_split`
- `model_eval_label`
- `model_eval_run`
- `model_eval_metric`

The production output tables remain model-specific, such as `model_01_market_regime`, because each model layer has a different business row shape.

Register the generic governance table names in `trading-manager` first, but do not register concrete column names yet. Column registration should wait until the SQL schema and first implementation slice are accepted.

### Consequences

- Evaluation/governance logic can be shared across all model layers.
- Layer-specific outputs stay clean and purpose-built.
- The registry has stable table-name vocabulary without prematurely locking column-level contracts.

## D014 - Implement initial generic model governance SQL schema

Date: 2026-04-30
Status: Accepted

### Context

The generic governance table names from D013 need a first concrete SQL shape before `MarketRegimeModel` evaluation can become reproducible. The schema must support the full evaluation chain without turning production model-output tables into generic catch-all tables.

The earlier data request boundary also needs to use current `feature` naming. Control-plane-facing requests should ask for source/feature data coverage only; label horizons, targets, split windows, and evaluation metrics remain model-local.

### Decision

Implement `src/model_governance/schema.py` as the first SQL helper for generic `trading_model` governance/evaluation tables, with `scripts/ensure_model_governance_schema.py` as the operational wrapper.

The first schema slice uses this dependency chain:

```text
model_dataset_request
-> model_dataset_snapshot
-> model_dataset_split
-> model_eval_label
-> model_eval_run
-> model_eval_metric
```

Table responsibilities:

- `model_dataset_request` records model-originated data coverage requests using `required_data_start_time`, `required_data_end_time`, `required_source_key`, and `required_feature_key`.
- `model_dataset_snapshot` freezes the feature table/version/time window/config metadata used for a reproducible experiment.
- `model_dataset_split` records time-series train/validation/test/holdout windows for a snapshot.
- `model_eval_label` records model-local labels by snapshot, target, horizon, available time, and label time.
- `model_eval_run` records a model/config/snapshot evaluation execution.
- `model_eval_metric` records metrics emitted by an evaluation run, optionally scoped by split, label, target, horizon, and factor.

JSONB payload columns are allowed as extension points, but stable shared fields should be promoted to explicit columns before other repositories depend on them.

### Consequences

- The schema is reusable across model layers while production output tables remain model-specific.
- `required_feature_key` supersedes older `required_derived_key` wording for active model data requests.
- Concrete registry column registration remains deferred until the schema is exercised by the first `MarketRegimeModel` evaluation harness and proves stable.
- Default tests use fake cursors and do not touch a durable database; runtime schema creation requires an explicit PostgreSQL target.
