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

ETF holdings are not primarily a `MarketRegimeModel` input. Their key role is to transmit sector/style strength from sector/industry ETF baskets into individual tradable stock candidates. The prior architecture jumped from market regime directly to strategy selection, which skipped the question of which symbols deserve strategy evaluation under the current regime.

### Decision

Add `SecuritySelectionModel` (`security_selection_model`) as Layer 2 between `MarketRegimeModel` and `StrategySelectionModel`.

`SecuritySelectionModel` owns target/security selection and universe construction. It uses market/sector/style context, sector/industry ETF holdings exposures, full-market scans, individual stock relative strength, liquidity, optionability, and event exclusions to produce long, short, watch, and excluded candidate pools.

### Rationale

Different market regimes require different selection styles. Risk-on regimes may prefer high-relative-strength core holdings of strong sector/industry ETFs; risk-off regimes may prefer defensive/low-volatility sector ETFs or stocks; rotation regimes may prefer newly strengthening industry ETF holdings or laggards catching up. This is a distinct modeling problem from choosing strategy family or signal entry quality.

### Consequences

- `MarketRegimeModel` should output broad market-state context useful for security selection, but should not output sector/style condition factors, ETF rankings, or security candidates; sector/style rotation belongs to `SecuritySelectionModel`.
- `etf_holding_snapshot` for eligible sector/industry equity ETFs becomes an important upstream data kind for Layer 2.
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

The useful downstream information is the concrete market-condition vector: trend, volatility stress, correlation stress, credit/rate/dollar/commodity pressure, broad market breadth, risk appetite, and transition pressure. Sector/industry rotation belongs to `SecuritySelectionModel`, not Model 1.

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
- Default tests use fake cursors and CLI dry-run modes, and do not touch a durable database.
- Runtime schema creation may use the development database directly; clear the `trading_model` development schema at the end of development runs with `scripts/clear_model_development_database.py`.

## D015 - Keep first MarketRegimeModel evaluation harness dry-run only

Date: 2026-04-30
Status: Accepted

### Context

The first `MarketRegimeModel` evaluation harness needs to exercise the generic governance/evaluation chain without allowing development-stage data to leak into the durable PostgreSQL database. At this stage, the goal is to validate row shapes, deterministic identifiers, chronological splits, future-label alignment, and metric calculations before promoting any runtime write path.

### Decision

Implement the first evaluation harness as dry-run only:

- reusable code lives in `src/model_evaluation/market_regime.py`;
- the operational wrapper is `scripts/evaluate_model_01_market_regime.py`;
- the wrapper accepts local JSONL feature/model rows or uses a deterministic built-in fixture;
- the wrapper prints a summary or optional local JSON artifact;
- it never imports `psycopg`, never accepts a database URL, and never opens a database connection.

The harness builds rows for the generic governance/evaluation tables in memory:

```text
model_dataset_request
model_dataset_snapshot
model_dataset_split
model_eval_label
model_eval_run
model_eval_metric
```

The initial labels are future shifted feature-return labels for SPY (`spy_return_1d` and `spy_return_5d`) and the initial metrics are basic counts, coverage, and Pearson correlations between model factors and labels.

### Consequences

- Development evaluation can be tested safely without mutating durable SQL state.
- A future database-writing path must be a separate reviewed change with explicit non-default write controls.
- The first harness is intentionally about plumbing and reproducibility, not yet about claiming model quality.

## D016 - Use development database with explicit cleanup instead of temporary SQL files

Date: 2026-04-30
Status: Accepted

### Context

Development work initially used local temporary SQL files to avoid writing any rows or tables into the configured database. Chentong clarified that, because the trading database currently has no durable production data, development work may use the database directly as long as the database is cleared after development.

### Decision

Do not make temporary SQL files the default development path.

`ensure_model_governance_schema.py` now creates the generic `trading_model` governance/evaluation tables by default and keeps `--dry-run` for stdout SQL inspection. `clear_model_development_database.py` clears the `trading_model` schema after development runs and requires an explicit confirmation token for destructive cleanup.

### Consequences

- Development can validate SQL paths against the configured database instead of only file output.
- Cleanup is scoped to the `trading_model` schema; scripts must not drop OpenClaw/system tables or unrelated component schemas.
- Default tests still use fake cursors and dry-run CLI paths so test runs do not mutate the database.

## D017 - Promotion infrastructure requires evaluation-backed candidates

Date: 2026-04-30
Status: Accepted

### Context

After the first `MarketRegimeModel` evaluation harness and generic governance schema, the next capability is promotion infrastructure. However, the system does not yet have real `feature_01_market_regime` or `model_01_market_regime` data, and no real evaluation metrics have been produced. Therefore the next step should add the durable promotion schema without claiming or executing any model promotion.

### Decision

Extend the generic `trading_model` governance schema with model configuration and promotion lifecycle tables:

```text
model_config_version
model_promotion_candidate
model_promotion_decision
model_promotion_rollback
```

`model_promotion_candidate` must reference both a `model_config_version` and a `model_eval_run`, so a candidate cannot exist without evaluation evidence. `model_promotion_decision` records approve/reject/defer style decisions for a candidate. `model_promotion_rollback` records a request to move away from an already promoted config version, optionally toward a previous config version.

This is promotion infrastructure only. It does not create an active production model pointer, does not mark any current model as promoted, and does not replace the need for real evaluation metrics.

### Consequences

- Promotion is evidence-backed by schema shape: candidates depend on evaluation runs.
- Promotion/rollback tables are generic across model layers while production output tables remain model-specific.
- Concrete column registration remains deferred; table-name registration lives in `trading-manager`.
- Actual promotion action remains blocked until real data, real metrics, and explicit acceptance thresholds exist.

## D018 - MarketRegimeModel feature SQL uses JSONB payload storage

Date: 2026-04-30
Status: Accepted

### Context

The development DB smoke test for the source → feature → model → evaluation chain found that the prior physical wide-column layout for `feature_01_market_regime` cannot safely materialize dense rows in PostgreSQL. PostgreSQL rejected a dense generated feature row with `row is too big: size 8768, maximum size 8160`.

The logical Layer 1 feature contract remains one point-in-time row per `snapshot_time`, but the generated feature surface is too high-dimensional to store as fixed physical `DOUBLE PRECISION` columns.

### Decision

Read `trading_data.feature_01_market_regime` as a table keyed by `snapshot_time` with generated feature values stored in `feature_payload_json` JSONB. The model SQL reader expands that payload into the in-memory feature dictionary before factor generation.

### Consequences

- `model_01_market_regime` remains a normal typed model-output table keyed by `available_time`.
- The feature generator can keep model-local generated feature keys without registering every generated feature as a physical column; after moving sector/industry rotation pairs and sector-observation aggregates to Layer 2, then pruning raw ratio moving-average level keys, the Layer 1 payload contains 870 logical keys.
- If specific generated features become cross-repository contracts, promote them separately instead of treating every generated key as a database column contract.

## D019 - Promotion gate uses agent review but not automatic promotion

Date: 2026-04-30
Status: Accepted

### Context

After the development DB smoke and promotion infrastructure, the next step is to evaluate whether a model config can be promoted. Chentong wants this step to be performed by a script that calls an agent to judge whether promotion is allowed.

### Decision

Add an agent-backed promotion review gate for `MarketRegimeModel`:

- `scripts/review_market_regime_promotion.py` builds a `model_config_version` row and an evaluation-backed `model_promotion_candidate` row from an evaluation summary.
- The script builds a strict reviewer-agent prompt and can invoke `openclaw agent` to return a constrained JSON decision.
- The script validates the agent output and converts it into a `model_promotion_decision` row.
- The script does not write the decision to PostgreSQL and does not create or change a production active-model pointer.

The reviewer prompt must reject/defer promotion if evidence is fixture-only, dry-run-only, missing real-data metrics, or missing explicit thresholds.

### Consequences

- Agent judgment becomes part of the promotion gate without giving the agent direct write authority over production state.
- Promotion remains evidence-backed and reviewable: candidate -> agent review -> decision row proposal.
- Actual persistence of the decision and any active production pointer remains a later explicit implementation step.


## D019 - ETF/security selection belongs to SecuritySelectionModel

Date: 2026-04-30
Status: Accepted

### Context

A temporary design placed per-ETF market-state affinity inside `MarketRegimeModel`. Chentong identified the boundary risk: ETF/security ranking inside Layer 1 can blur the separation between state description and downstream selection, and increases the chance that evaluation labels such as future return leak into production state construction.

The current market-state vector should help downstream selection, but it should not itself select ETFs or stocks.

### Decision

Remove per-ETF affinity/ranking from `MarketRegimeModel` V1. Layer 1 returns only the continuous point-in-time market-state vector keyed by `available_time`.

`SecuritySelectionModel` owns candidate-level selection-parameter construction for sector/industry ETFs and stocks. It may consume the Layer 1 state vector, sector/industry ETF and stock trend features, relative strength, ETF holdings exposure, liquidity, optionability, and event exclusions to adjust each candidate's selection parameter.

The Layer 2 parameter objective is not maximum realized or expected return. The final `candidate_selection_parameter` should be higher for the clearest and most certain tradable trend: trend clarity, trend persistence, relative strength consistency, signal agreement, adequate liquidity/optionability, and controlled event/volatility ambiguity. Future returns are evaluation labels for calibration, not direct production ranking inputs.

### Consequences

- `model_01_market_regime` remains a pure state-description output.
- No `model_01_market_regime_etf_affinity` output is produced by Model 1.
- Model 2 should define candidate state features such as `trend_clarity_score`, `trend_persistence_score`, and `certainty_score`, plus a final `candidate_selection_parameter`.
- Evaluation may still ask whether high-parameter, high-certainty trends later performed well, but that is downstream validation rather than Layer 1 construction.


## D020 - SecuritySelectionModel ETF candidates are sector/industry ETFs only

Date: 2026-04-30
Status: Accepted

### Context

Layer 2 needs to choose ETFs and stocks, but not every ETF used by the platform should be a tradable candidate. Broad index ETFs, style proxies, rates, credit, commodity, dollar, volatility, and other macro ETFs are useful for state detection, benchmarking, relative-strength context, and risk filtering. They do not provide the same sector/industry holdings bridge into stock selection.

### Decision

`SecuritySelectionModel` V1 selects ETFs only from eligible sector/industry equity ETFs. These ETFs must represent a sector, industry, or similarly stock-holdings-based business basket that can transmit into `stock_etf_exposure`.

Broad market/style ETFs such as `SPY`, `QQQ`, `IWM`, `DIA`, and `RSP`, and non-equity macro/cross-asset ETFs such as `TLT`, `IEF`, `SHY`, `GLD`, `SLV`, `DBC`, `USO`, `UUP`, `VIXY`, `HYG`, and `LQD`, are excluded from the V1 ETF candidate universe. They may remain upstream features, benchmarks, filters, or risk context.

### Consequences

- Layer 2 ETF output should be parameter rows such as `candidate_type = industry_etf` with `candidate_selection_parameter`, rather than names implying the model directly selects a preferred ETF list.
- ETF holdings exposure work should prioritize sector/industry equity ETFs.
- Model 2 still adjusts candidate parameters according to trend clarity, persistence, certainty, and tradability, not by highest realized or expected return.
- Direct trading of broad/macro ETFs, if ever needed, should be modeled as a separate later scope rather than mixed into `SecuritySelectionModel` V1.


## D021 - SecuritySelectionModel derives market parameters for candidate vectors

Date: 2026-04-30
Status: Accepted

### Context

The bridge from market state to target selection should be explicit. Passing the full Layer 1 vector directly into every ETF/stock parameter is hard to interpret, while selecting ETFs inside Layer 1 would blur model boundaries and raise leakage risk. Chentong proposed compressing the broad market vector into a market parameter that becomes part of each target candidate vector.

The parameter should focus on trend certainty and broad-market turning risk. Because sectors respond differently to the same broad tape, each sector/industry ETF should also have its own weighted market parameter. Stocks that do not map into the eligible sector/industry ETF universe should use the unweighted base market parameter.

### Decision

`SecuritySelectionModel` owns the transformation from `model_01_market_regime` into candidate-level market-parameter fields. The initial conceptual fields are:

- `market_trend_certainty_parameter`;
- `market_transition_risk_parameter`;
- `base_market_parameter`;
- `sector_weighted_market_parameter`;
- `candidate_market_parameter`;
- `candidate_selection_parameter`.

For sector/industry ETF candidates, `candidate_market_parameter` equals that ETF's sector-weighted market parameter. For stock candidates with sector/industry ETF exposure, it is the exposure-weighted blend of the mapped ETF market parameters. For unmapped stocks, it falls back to `base_market_parameter`.

`candidate_selection_parameter` is the final Model 2 parameter for each candidate. It is adjusted using the candidate market parameter and the candidate's own trend/certainty/tradability/risk state. Ranking or choosing the highest value is a downstream usage pattern, not the persisted model-output contract.

### Consequences

- Model 1 remains a pure market-state vector; Model 2 creates the selection-facing parameters.
- Model 2 candidate vectors include both market parameter and target-specific state: trend clarity, trend persistence, certainty, relative strength, liquidity, optionability, and event risk.
- Sector/industry ETF parameter rows can be sorted by downstream users, but Model 2 itself should persist the parameter surface rather than a selected ETF list.
- The first Model 2 implementation needs an explicit sector factor-weight matrix mapping Layer 1 factors to eligible sector/industry ETFs.
- Field names remain model-local until implementation proves the shape and any shared registry registration is reviewed.


## D022 - SecuritySelectionModel output is an adjusted parameter surface, not top-candidate selection

Date: 2026-04-30
Status: Accepted

### Context

A previous sketch expressed Model 2 as an additive `target_score` formula and examples showed preferred ETF/candidate lists. Chentong clarified that this is the wrong contract: Model 2's main responsibility is to adjust a candidate-level parameter. Selecting the highest-parameter ETF is how a downstream consumer uses the parameter surface, not what Model 2 itself outputs.

### Decision

Define Model 2's core output as candidate-level parameter rows keyed by `available_time + candidate_symbol` with a final `candidate_selection_parameter` and supporting candidate state fields.

Do not define the model contract as direct `+ w` / `- w` arithmetic, a top-ETF picker, or a preferred ETF list. A linear formula may be tested later as one implementation candidate, but the durable contract is a parameter-adjustment surface.

### Consequences

- Replace `target_score`/preferred-list language with `candidate_selection_parameter` and candidate parameter rows.
- Ranking, top-N selection, and choosing the highest sector/industry ETF are downstream usage of Model 2 output.
- Model 2 acceptance should test parameter stability, point-in-time correctness, monotonic sanity, and calibration against future labels, not whether the model directly emits one chosen ETF.


## D023 - MarketRegimeModel factors describe deep market properties

Date: 2026-04-30
Status: Accepted

### Context

The initial `MarketRegimeModel` factor set used many observable proxy groupings and ETF-pair relationships. Those signals are useful evidence, but Chentong clarified that the desired Model 1 output is not an ETF-ratio dashboard. It should describe deeper market properties: price, trend, capital/flow/funding, sentiment, valuation, fundamentals, macro, structure, and risk.

### Decision

Treat observable ratios, spreads, returns, relative-strength pairs, volatility measures, breadth measures, and other market data as measurement signals. The canonical Model 1 factor ontology should describe latent market properties:

- price behavior;
- trend certainty;
- capital flow and funding/liquidity;
- sentiment and risk appetite;
- valuation and discount-rate pressure;
- fundamental strength and growth quality;
- macro and policy environment;
- market-wide structure, breadth, concentration, crowding, and correlation;
- risk stress, tail pressure, and transition risk.

### Consequences

- Model 1 should move from surface proxy labels toward market-property factor names such as `price_behavior_factor`, `trend_certainty_factor`, `capital_flow_factor`, `sentiment_factor`, `valuation_pressure_factor`, `fundamental_strength_factor`, `macro_environment_factor`, `market_structure_factor`, `risk_stress_factor`, and `transition_risk_factor`.
- ETF ratios such as `HYG/LQD`, `TLT/SHY`, `QQQ/SPY`, or `GLD/SPY` may remain input evidence, but they should not be treated as the conceptual factor itself.
- Existing V1 fields remain a provisional implementation slice until a reviewed migration updates the concrete output schema, config, tests, registry references, and downstream Model 2 parameterization.
- Evaluation should inspect whether each latent market-property factor has stable, interpretable evidence support and downstream usefulness, not merely whether one proxy ratio correlates with a future label.


## D024 - MarketRegimeModel must increase input evidence coverage deliberately

Date: 2026-04-30
Status: Accepted

### Context

Chentong flagged the initial evidence usage as too low when `model_01_market_regime` used only a narrow hand-selected slice of the Layer 1 feature payload. After the first reviewed expansion and raw ratio-MA pruning, `feature_01_market_regime` contains 870 Layer 1 logical feature keys and `model_01_market_regime` uses 336 signal columns across 9 provisional factors, about 38.6% feature utilization.

The issue is not that every generated feature must be forced into every factor. Some columns should remain quality controls, diagnostics, redundant checks, fallback evidence, future-review candidates, or evaluation-only fields. But underusing the reviewed input surface risks collapsing Model 1 back into a shallow ETF-ratio dashboard.

### Decision

Model 1 should deliberately increase evidence coverage through an explicit feature-to-latent-factor evidence map. The map should assign generated feature columns to market-property factors by measurement family, role, direction, history requirements, and rationale.

The target is broad, explainable coverage of the input evidence universe, not indiscriminate all-column ingestion.

### Consequences

- Add or maintain a reviewed evidence map for `model_01_market_regime` before major factor expansion.
- Track evidence utilization as an acceptance metric: total generated feature keys, keys assigned to a latent market-property factor, keys used only for data quality/diagnostics/evaluation, and keys intentionally unused.
- Keep factors interpretable by grouping evidence into the accepted market-property ontology instead of adding opaque high-dimensional raw features directly to the output vector.
- Future implementation work should continue expanding or pruning from the current 336-column provisional slice while preserving point-in-time correctness and no-leakage rules.


## D025 - Sector and industry rotation belongs to SecuritySelectionModel

Date: 2026-04-30
Status: Accepted

### Context

Model 1 was drifting toward a mixed responsibility: a broad market-state vector plus a `sector_rotation_factor` derived from sector ETF dispersion and sector-vs-broad relative-strength proxies. Chentong clarified that sector rotation is not merely one broad market property. It is the core research problem for Model 2: compare sector/industry ETF and stock candidates under the same broad market state. Chentong later accepted moving all sector/industry rotation-related evidence to Layer 2 so Layer 1 can stay clean.

### Decision

Move sector/industry rotation, sector leadership, industry leadership, sector-vs-sector relative-strength comparison, and sector-observation breadth/dispersion aggregates out of `MarketRegimeModel` and into `SecuritySelectionModel`.

`MarketRegimeModel` may retain broad-market structure fields such as concentration, crowding, broad-asset correlation stress, dispersion, and transition pressure when they are derived from the market-state or cross-asset macro/risk universe and describe the overall tape. It must not consume or output sector/industry rotation evidence, sector-observation participation evidence, candidate-facing sector rotation conclusions, sector rankings, preferred sector lists, or sector/industry leadership parameters.

### Consequences

- Remove `sector_rotation_factor` from the Model 1 output contract and current factor configuration.
- Treat sector/industry ETF relative-strength and sector-observation breadth/dispersion evidence as Model 2 evidence, even when aggregated without a single candidate identity.
- `SecuritySelectionModel` owns sector/industry rotation research, sector-weighted candidate parameters, ETF holdings exposure propagation into stocks, and candidate-level certainty comparisons.
- The apparent Model 1 input-utilization denominator is reduced after removing both sector/industry rotation pair features and `sector_observation_*` aggregate features from `feature_01_market_regime`.


## D026 - Cross-asset macro proxies may remain Model 1 evidence

Date: 2026-04-30
Status: Accepted

### Context

After moving sector/industry rotation to `SecuritySelectionModel`, Chentong pointed out that Model 1 still uses long/short bond ratios such as `TLT/SHY` or `IEF/SHY`. This is a valid boundary question: both sector rotation and rate proxies can be expressed as ETF ratios, but they answer different model questions.

### Decision

Do not classify all ETF ratios the same way.

Cross-asset macro/risk proxies may remain Model 1 evidence when they describe broad market properties rather than candidate choice. Examples include:

- `TLT/SHY` and `IEF/SHY` as evidence for discount-rate, duration, and term-structure pressure;
- `HYG/LQD` as evidence for credit/funding stress;
- dollar, commodity, volatility, and safe-haven ratios as evidence for liquidity pressure, inflation impulse, risk aversion, or macro driver dominance.

Sector/industry ETF-vs-ETF or sector-vs-broad comparisons belong to Model 2 when they answer which sector, industry, ETF, or stock candidate has stronger leadership/certainty.

### Consequences

- Model 1 may use long/short bond ratios and other cross-asset macro sensors as input evidence.
- Model 1 should not output durable ratio-named factors such as a literal `tlt_shy_factor`; the output should be latent market-property fields such as `discount_rate_pressure_factor`, `funding_credit_stress_factor`, `dollar_liquidity_pressure_factor`, `inflation_commodity_impulse_factor`, or `risk_stress_factor` after schema review.
- Current `rate_pressure_factor` remains a provisional implementation name and should be migrated toward the deeper ontology, likely `discount_rate_pressure_factor`, when the Model 1 output schema is reviewed.
- Model 2 V1 remains focused on sector/industry equity ETF and stock candidate parameterization; broad/macro ETFs are context/filter evidence, not V1 tradable candidates.

## D027 - Expand reviewed Model 1 evidence and prune low-value generated features

Date: 2026-04-30
Status: Accepted

### Context

Chentong asked to continue expanding the data usage surface, and to stop generating data if it is not actually useful. After sector/industry rotation evidence moved to Layer 2, Model 1 still used only a narrow hand-selected slice of the remaining Layer 1 feature payload. At the same time, Feature 01 still generated raw ratio moving-average level keys, which are scale-dependent and less robust than normalized trend measures.

### Decision

Expand `model_01_market_regime` factor specifications to use a broader reviewed set of Layer 1 evidence across trend, volatility stress, correlation stress, credit stress, rate pressure, dollar pressure, commodity pressure, broad-market breadth, and risk appetite. The expansion uses normalized returns, distance-to-moving-average, moving-average slope, MA spread/alignment, volatility level/ratio/percentile/z-score, and reviewed broad/cross-asset correlation evidence.

Do not treat raw ratio moving-average level keys as durable evidence. Those generated features should be pruned from Feature 01/Feature 02 unless a later review defines a stable use that is not covered by distance/slope/spread/alignment features.

### Consequences

- Current Model 1 evidence usage rises to 336 configured signal columns out of 870 Layer 1 feature keys, about 38.6% reviewed utilization.
- All configured Model 1 signals are present in the Layer 1 payload.
- Layer 1 still avoids sector/industry rotation and sector-observation evidence; those remain Layer 2 responsibilities.
- Remaining unused generated keys should continue through the evidence-map process: assign to latent factor, diagnostic/quality/evaluation-only, future-review, or remove from generation.
