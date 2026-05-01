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

## D006 - SecuritySelectionModel bridges sector rotation to tradable symbols

Date: 2026-04-28

### Context

ETF holdings are not primarily a `MarketRegimeModel` input. Their key role is to transmit sector/industry rotation strength from sector/industry ETF baskets into individual tradable stock candidates. The prior architecture jumped from broad market state directly to strategy selection, which skipped the question of which symbols deserve strategy evaluation based on sector rotation and candidate evidence.

### Decision

Add `SecuritySelectionModel` (`security_selection_model`) as Layer 2 between `MarketRegimeModel` and `StrategySelectionModel`.

`SecuritySelectionModel` owns target/security selection and universe construction. It uses sector/industry rotation context, sector/industry ETF holdings exposures, full-market scans, individual stock relative strength, liquidity, optionability, and event exclusions to produce long, short, watch, and excluded candidate pools. Broad market state may be retained as background/audit or coarse gating context, but it is not the direct stock selector.

### Rationale

Different sector/industry rotation states imply different candidate pools. Strong leadership may prefer high-relative-strength core holdings of strong sector/industry ETFs; broad but early rotation may prefer newly strengthening industry ETF holdings; unstable or narrow leadership may gate candidates into watch-only status. This is a distinct modeling problem from choosing strategy components, signal entry quality, option expression, or execution/risk policy.

### Consequences

- `MarketRegimeModel` should output broad market-state context useful for option expression, strategy compatibility, and execution/risk policy, but should not output sector/style condition factors, ETF rankings, or security candidates; sector/style rotation belongs to `SecuritySelectionModel`.
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

- `price_behavior_factor`
- `trend_certainty_factor`
- `capital_flow_factor`
- `sentiment_factor`
- `valuation_pressure_factor`
- `fundamental_strength_factor`
- `macro_environment_factor`
- `market_structure_factor`
- `risk_stress_factor`
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
- `trend_certainty_factor` uses `bucketed_mean`, first averaging trend signals by ETF/symbol bucket and then reducing across ETF buckets.

Clarify semantics:

- `macro_environment_factor` means commodity-related assets are becoming a dominant market driver; it is not automatically bearish.
- `valuation_pressure_factor` means long-duration bonds are weakening versus short-duration bonds; safe-haven bond strength may become a separate factor later.

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
- The feature generator can keep model-local generated feature keys without registering every generated feature as a physical column; after moving sector/industry rotation pairs and sector-observation aggregates to Layer 2, then pruning raw ratio moving-average level keys and standalone SHY return/trend keys, the Layer 1 payload contains 857 logical keys.
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

The current market-state vector is downstream background context, but it should not itself select ETFs, sectors, or stocks. Its more direct uses are option-expression constraints, strategy compatibility, and execution/risk policy.

### Decision

Remove per-ETF affinity/ranking from `MarketRegimeModel` V1. Layer 1 returns only the continuous point-in-time market-state vector keyed by `available_time`.

`SecuritySelectionModel` owns candidate-level selection-parameter construction for sector/industry ETFs and stocks. It may retain the Layer 1 state vector as background/audit/coarse-gating context, but candidate ranking should be driven by sector/industry ETF and stock trend features, relative strength, ETF holdings exposure, liquidity, optionability, and event exclusions.

The Layer 2 parameter objective is not maximum realized or expected return. The final `candidate_selection_parameter` should be higher for the clearest and most certain tradable trend: trend clarity, trend persistence, relative strength consistency, signal agreement, adequate liquidity/optionability, and controlled event/volatility ambiguity. Future returns are evaluation labels for calibration, not direct production ranking inputs.

### Consequences

- `model_01_market_regime` remains a pure state-description output.
- No `model_01_market_regime_etf_affinity` output is produced by Model 1.
- Model 2 should define sector/industry rotation and candidate state features such as `sector_rotation_state_vector`, `trend_clarity_score`, `trend_persistence_score`, and `certainty_score`, plus any optional `candidate_selection_parameter`.
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


## D021 - SecuritySelectionModel preserves market-state vector context for candidate vectors

Date: 2026-04-30
Status: Superseded by D029

### Context

Supersession note: D029 refines this decision. The key durable part is "do not collapse the Layer 1 vector into one scalar"; the superseded part is assigning Model 2 a direct candidate market-context vector bridge from Layer 1. Market state is now treated primarily as background for option expression and execution/risk policy, while security selection is sector-rotation driven.

The bridge from market state to target selection should be explicit. Layer 1 correctly compresses the broad input surface into a compact market-state vector, but Chentong clarified that the next layer should not compress that 9-dimensional state vector into one deterministic market parameter. A single scalar would hide important differences such as trend strength versus rate pressure, credit stress versus volatility stress, or commodity impulse versus risk appetite.

Layer 2 still needs an interpretable candidate-facing transformation, but that transformation should preserve the vector structure. Sector/industry ETFs and stocks may weight the Layer 1 factors differently, yet the result should remain a candidate market-context vector or parameter bundle rather than one collapsed value.

### Decision

`SecuritySelectionModel` owns the transformation from `model_01_market_regime` into candidate-level market-context vectors. The initial conceptual fields are:

- `base_market_context_vector`;
- `sector_weighted_market_context_vector`;
- `candidate_market_context_vector`;
- `market_trend_certainty_component`;
- `market_transition_risk_component`;
- `candidate_selection_parameter` only as an optional/convenience scalar derived from the full candidate parameter surface, not as the sole durable market-context representation.

For sector/industry ETF candidates, `candidate_market_context_vector` equals that ETF's sector-weighted transformation of the Layer 1 vector. For stock candidates with sector/industry ETF exposure, it is the exposure-weighted blend of the mapped ETF market-context vectors. For unmapped stocks, it falls back to `base_market_context_vector`.

Do not define `market_parameterizer(model_01_market_regime_vector) -> scalar` as the Model 2 bridge. Any scalar ranking parameter must remain downstream/convenience information and must be accompanied by the underlying candidate market-context vector and candidate state fields.

### Consequences

- Model 1 remains a pure 9-factor market-state vector; Model 2 creates selection-facing candidate context without collapsing the market state into one scalar.
- Model 2 candidate rows should include both market context and target-specific state: trend clarity, trend persistence, certainty, relative strength, liquidity, optionability, and event risk.
- Sector/industry ETF parameter rows can be sorted by downstream users if a scalar is produced, but Model 2 itself should persist the parameter surface/vector rather than only a selected ETF list or one market scalar.
- The first Model 2 implementation needs an explicit sector factor-weight matrix or vector transform mapping Layer 1 factors to eligible sector/industry ETFs.
- Field names remain model-local until implementation proves the shape and any shared registry registration is reviewed.


## D022 - SecuritySelectionModel output is an adjusted parameter surface, not top-candidate selection

Date: 2026-04-30
Status: Accepted

### Context

A previous sketch expressed Model 2 as an additive `target_score` formula and examples showed preferred ETF/candidate lists. Chentong clarified that this is the wrong contract: Model 2's main responsibility is to adjust a candidate-level parameter. Selecting the highest-parameter ETF is how a downstream consumer uses the parameter surface, not what Model 2 itself outputs.

### Decision

Define Model 2's core output as candidate-level parameter rows keyed by `available_time + candidate_symbol` with sector/industry rotation context, supporting candidate state fields, and any derived `candidate_selection_parameter` clearly marked as a convenience/ranking scalar rather than the only durable representation.

Do not define the model contract as direct `+ w` / `- w` arithmetic, a top-ETF picker, or a preferred ETF list. A linear formula may be tested later as one implementation candidate, but the durable contract is a parameter-adjustment surface.

### Consequences

- Replace `target_score`/preferred-list language with candidate parameter rows that preserve sector/industry rotation context; `candidate_selection_parameter` may exist only as a derived convenience scalar.
- Ranking, top-N selection, and choosing the highest sector/industry ETF are downstream usage of Model 2 output and should not require discarding the underlying rotation/context evidence.
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

Chentong flagged the initial evidence usage as too low when `model_01_market_regime` used only a narrow hand-selected slice of the Layer 1 feature payload. After the reviewed expansion plus raw ratio-MA and orphan SHY-trend pruning, `feature_01_market_regime` contains 857 Layer 1 logical feature keys and `model_01_market_regime` uses 857 signal columns across 9 provisional factors, 100% reviewed feature ownership.

The issue is not that every generated feature must be forced into every factor. Some columns should remain quality controls, diagnostics, redundant checks, fallback evidence, future-review candidates, or evaluation-only fields. But underusing the reviewed input surface risks collapsing Model 1 back into a shallow ETF-ratio dashboard.

### Decision

Model 1 should deliberately increase evidence coverage through an explicit feature-to-latent-factor evidence map. The map should assign generated feature columns to market-property factors by measurement family, role, direction, history requirements, and rationale.

The target is broad, explainable coverage of the input evidence universe, not indiscriminate all-column ingestion.

### Consequences

- Add or maintain a reviewed evidence map for `model_01_market_regime` before major factor expansion.
- Track evidence utilization as an acceptance metric: total generated feature keys, keys assigned to a latent market-property factor, keys used only for data quality/diagnostics/evaluation, and keys intentionally unused.
- Keep factors interpretable by grouping evidence into the accepted market-property ontology instead of adding opaque high-dimensional raw features directly to the output vector.
- Future implementation work should continue expanding or pruning from the current 857-column provisional slice while preserving point-in-time correctness and no-leakage rules.


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
- `SecuritySelectionModel` owns sector/industry rotation research, sector/industry rotation state/context, ETF holdings exposure propagation into stocks, and candidate-level certainty comparisons.
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
- Model 1 should not output durable ratio-named factors such as a literal `tlt_shy_factor`; the output should be latent market-property fields such as `discount_valuation_pressure_factor`, `funding_capital_flow_factor`, `dollar_liquidity_pressure_factor`, `inflation_commodity_impulse_factor`, or `risk_stress_factor` after schema review.
- Current `valuation_pressure_factor` remains a provisional implementation name and should be migrated toward the deeper ontology, likely `discount_valuation_pressure_factor`, when the Model 1 output schema is reviewed.
- Model 2 V1 remains focused on sector/industry equity ETF and stock candidate parameterization; broad/macro ETFs are context/filter evidence, not V1 tradable candidates.

## D027 - Expand reviewed Model 1 evidence and prune low-value generated features

Date: 2026-04-30
Status: Accepted

### Context

Chentong asked to continue expanding the data usage surface, and to stop generating data if it is not actually useful. After sector/industry rotation evidence moved to Layer 2, Model 1 still used only a narrow hand-selected slice of the remaining Layer 1 feature payload. At the same time, Feature 01 still generated raw ratio moving-average level keys, which are scale-dependent and less robust than normalized trend measures.

### Decision

Expand `model_01_market_regime` factor specifications to use a broader reviewed set of Layer 1 evidence across trend, volatility stress, correlation stress, credit stress, rate pressure, dollar pressure, commodity pressure, broad-market breadth, and risk appetite. The expansion uses normalized returns, distance-to-moving-average, moving-average slope, MA spread/alignment, volatility level/ratio/percentile/z-score, and reviewed broad/cross-asset correlation evidence.

Do not treat raw ratio moving-average level keys or standalone SHY return/trend keys as durable evidence. Those generated features should be pruned from Feature 01/Feature 02 unless a later review defines a stable use that is not covered by distance/slope/spread/alignment features, rate-pair evidence, or volatility evidence.

### Consequences

- Current Model 1 evidence usage rises to 857 configured signal columns out of 857 Layer 1 feature keys, 100% reviewed ownership.
- All configured Model 1 signals are present in the Layer 1 payload, and every Layer 1 payload key is currently owned by the Model 1 signal configuration.
- Layer 1 still avoids sector/industry rotation and sector-observation evidence; those remain Layer 2 responsibilities.
- Future generated keys should not be added without an owner: Model 1 signal, diagnostic/quality/evaluation role, future-review note, or immediate removal from generation.

## D028 - Do not collapse market-state vector into a single Model 2 market scalar

Date: 2026-04-30
Status: Superseded by D029

### Context

Supersession note: D029 keeps the no-scalar-collapse rule but moves the primary market-state consumers away from Model 2 candidate ranking and toward option expression plus execution/risk policy.

After Model 1 reached a compact 9-factor market-state vector, Chentong clarified that the vector shape is acceptable, but compressing that vector again into one deterministic market parameter for Model 2 would lose too much information. The issue is not Layer 1's 9-factor compression; it is the proposed next-stage scalar `base_market_parameter` / `candidate_market_parameter` bridge.

### Decision

Model 2 must preserve the Layer 1 vector structure when creating candidate-facing market context. Use candidate market-context vectors or parameter bundles, such as `base_market_context_vector`, `sector_weighted_market_context_vector`, and `candidate_market_context_vector`, instead of scalar market parameters.

A scalar `candidate_selection_parameter` may exist only as a downstream/convenience projection for ranking or UI, and must not be the sole persisted representation of candidate context.

### Consequences

- The Model 2 bridge is vector-preserving: factor weighting changes component emphasis but does not collapse the Layer 1 state into one number.
- Candidate rows should retain market-context vector fields plus candidate-specific trend/certainty/tradability/risk fields.
- Downstream ranking can still consume a scalar projection, but analysis, calibration, and later models must be able to inspect the underlying vector context.


## D029 - Market state is background for option expression and execution policy

Date: 2026-04-30
Status: Accepted

### Context

Chentong clarified the model boundary after the vector-preserving Model 2 bridge discussion. The broad market state is important, but it is still background. The system trades concrete underlyings and option contracts, and the final trading strategy is a composite assembled from multiple strategy components.

Therefore the most direct uses of `MarketRegimeModel` are not stock selection. They are:

1. helping `OptionExpressionModel` choose the appropriate contract expression and constraints;
2. helping `PortfolioRiskModel` / execution-gate logic choose risk budget, execution style, and exit posture.

Stock and ETF candidate selection should be driven primarily by sector/industry rotation and candidate-specific trend/certainty evidence.

### Decision

Treat `model_01_market_regime` as broad market background rather than a direct stock/sector selector.

- `SecuritySelectionModel` should use sector/industry rotation, ETF holdings exposure, candidate trend/relative-strength evidence, liquidity, optionability, and event exclusions to construct candidate parameter rows. It may reference market state for audit or coarse gating, but it should not rank stocks by applying a sector-weighted transform to the Layer 1 vector.
- `StrategySelectionModel` should compose multiple strategy components into a final comprehensive strategy recommendation instead of selecting one historical champion strategy in isolation. Market state can inform component eligibility/weighting, but candidate selection remains rotation/candidate-evidence driven.
- `OptionExpressionModel` should consume market state directly when deciding contract constraints such as DTE, delta/moneyness, IV/vega/theta tolerance, holding horizon, and no-trade filters.
- `PortfolioRiskModel` should consume market state directly when deciding risk budget, position sizing, order aggressiveness, slippage tolerance, overnight permission, exit strictness, and kill-switch posture.

### Consequences

- D021 and D028 are refined/superseded: the no-scalar-collapse rule remains valid, but Model 2 no longer owns a direct Layer-1-to-candidate market-context vector bridge.
- Model 2 implementation should prioritize `feature_02_security_selection`, sector/industry rotation state, ETF holdings exposure, and candidate trend/certainty surfaces.
- Later implementation should define explicit market-state-to-option-expression and market-state-to-execution-policy contracts before treating Layer 1 as production-ready for downstream use.
- Unified decision records should preserve Layer 1 state separately from Layer 2 candidate rotation context, then show how Layer 5 and Layer 7 used market state.

## D030 - Use nine-part decomposition for model layer design

Date: 2026-05-01
Status: Accepted

### Context

The seven-layer architecture needs a consistent way to review each model before implementation details, feature contracts, training logic, evaluation harnesses, or promotion gates expand. Chentong accepted a direct decomposition method: data, features, prediction target, model mapping, loss, training updates, validation, overfitting control, and deployment into the real decision process.

### Decision

Use the nine-part model decomposition in `docs/08_model_decomposition.md` as the standard design and review template for every `trading-model` layer:

1. data;
2. features;
3. prediction target;
4. model mapping from `X` to `y` or to the output vector/parameter surface;
5. loss or error measure;
6. training/update process;
7. validation/usefulness;
8. overfitting control;
9. deployment into the offline decision flow.

The template applies to supervised models, unsupervised state-vector models, rankers, overlays, parameter surfaces, and risk gates. It does not require every layer to become a supervised `X -> y` predictor.

### Consequences

- Layer design docs should identify what `X`, `y`, loss, validation, and deployment mean for that layer before implementation expands.
- `MarketRegimeModel` remains unsupervised in V1: its target is a continuous market-state vector rather than a future-return label or hard regime class.
- Future layer specs should use this structure before adding new code paths, schemas, or registry proposals.
- Open gaps for incomplete layer decompositions stay in `docs/04_task.md` until reviewed.

## D031 - MarketRegimeModel output columns use market-property factors

Date: 2026-05-01
Status: Accepted

### Context

The prior `model_01_market_regime` implementation still exposed proxy-dashboard factor names such as trend, volatility stress, correlation stress, credit stress, rate pressure, dollar pressure, commodity pressure, breadth, and risk appetite. Chentong clarified that Layer 1 should now become a market-property vector, not merely a set of observable proxy groupings.

### Decision

Migrate the `model_01_market_regime` output factor contract to market-property columns:

- `price_behavior_factor`
- `trend_certainty_factor`
- `capital_flow_factor`
- `sentiment_factor`
- `valuation_pressure_factor`
- `fundamental_strength_factor`
- `macro_environment_factor`
- `market_structure_factor`
- `risk_stress_factor`
- `transition_pressure`
- `data_quality_score`

Observable proxy signals remain valid sensors inside `config/factor_specs.toml`, but proxy categories are no longer the public output ontology. The current `fundamental_strength_factor` uses broad-market participation evidence as a provisional proxy until true point-in-time fundamental data is available.

### Consequences

- `factor_specs.toml`, evaluation fixtures, tests, and documentation use market-property output names.
- Price behavior and trend certainty are split instead of being collapsed into one trend proxy.
- Dollar and commodity pressure evidence is treated as macro-environment evidence rather than separate public output factors.
- Downstream consumers should read Layer 1 as broad market properties, not as sector/security selection signals.

## D032 - MarketRegimeModel Layer 1 V1 contract is settled

Date: 2026-05-01
Status: Accepted

### Context

After migrating the Layer 1 output from proxy-dashboard factors into market-property factors, Chentong reviewed the Layer 1 decomposition and accepted the current direction as settled for V1.

### Decision

Treat `MarketRegimeModel` Layer 1 V1 as accepted with this contract:

- input is `trading_data.feature_01_market_regime`;
- output is `trading_model.model_01_market_regime` keyed by `available_time`;
- output factors are market-property fields: price behavior, trend certainty, capital/funding flow, sentiment, valuation pressure, fundamental strength, macro environment, market structure, risk stress, transition pressure, and data quality;
- V1 remains unsupervised and does not require clustering, hard regime labels, or future-return targets;
- Layer 1 is broad market background for strategy compatibility, option expression, and portfolio risk/execution policy;
- Layer 1 must not rank sectors, ETFs, or securities.

### Consequences

- Further Layer 1 work should be refinement, evidence maturation, evaluation, and promotion-readiness rather than reopening the core output ontology.
- Remaining architecture work should move to the nine-part decompositions for Layers 2-7, starting with `SecuritySelectionModel`.
- Any future Layer 1 schema change requires a new decision because downstream consumers can now treat the market-property vector as the V1 contract.

## D033 - Start SecuritySelectionModel from candidate parameter surface decomposition

Date: 2026-05-01
Status: Draft

### Context

After settling `MarketRegimeModel` Layer 1 V1, the next layer is `SecuritySelectionModel`. Existing accepted boundaries already state that Layer 2 owns sector/industry ETF and stock candidate parameter construction, while Layer 1 remains broad market background.

### Draft Direction

Start Layer 2 from the nine-part decomposition in `docs/08_model_decomposition.md`:

- use `trading_data.feature_02_security_selection` as the home for sector/industry rotation and daily-context evidence moved out of `feature_01_market_regime`, plus sector/industry ETF holdings, `stock_etf_exposure`, candidate trend/liquidity/optionability/event evidence, and Layer 1 only as background/audit/coarse-gating context;
- output a candidate parameter surface keyed by `available_time + candidate_symbol`;
- include both sector/industry ETF holdings-driven candidates and full-market scan-driven candidates;
- keep `candidate_selection_parameter` as an optional convenience scalar, not the only durable output;
- evaluate against future labels only after construction, never as direct production ranking inputs.

### Open Review Points

- Exact V1 output table name and row shape.
- Whether `stock_etf_exposure` is produced in `trading-data`, `trading-model`, or shared contracts after proof.
- First eligible sector/industry ETF basket and base stock universe.
- First parameter-adjustment method and gating thresholds.

## D034 - Feature 2 owns migrated sector rotation evidence

Date: 2026-05-01
Status: Accepted

### Context

Layer 2 decomposition review started by clarifying the data surface. Chentong confirmed that `feature_02_security_selection` should contain the sector/industry rotation evidence previously moved out of `feature_01_market_regime`.

### Decision

Settle `feature_02_security_selection` V1 as the Feature 2 input surface for migrated Layer 1 rotation evidence:

- candidate-comparison rows for reviewed relative-strength combinations with `combination_type in {sector_rotation, daily_context}`;
- one `sector_rotation_summary` row per snapshot for sector-observation breadth, participation, and dispersion evidence;
- physical table columns are the seven metadata columns plus `feature_payload_json`;
- row key is `snapshot_time + candidate_symbol + comparison_symbol + rotation_pair_id`;
- current shared contract is 32 rows per snapshot: 1 summary row, 18 `sector_rotation` rows, and 13 `daily_context` rows;
- current logical payload has 24 keys: 16 relative-strength/trend/volatility/correlation keys and 8 sector-observation breadth/dispersion keys.

### Consequences

- Do not reintroduce these sector/industry rotation payloads into `feature_01_market_regime`.
- `SecuritySelectionModel` should consume Feature 2 rows as its initial sector/industry rotation evidence before adding holdings exposure, full-market scan, liquidity, optionability, and event overlays.
- Future Feature 2 changes should preserve the point-in-time row key and document any new payload keys or row types.
