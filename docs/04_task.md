# Task

## Active Tasks

- Review and refine the first `MarketRegimeModel` implementation slice: a point-in-time continuous market-state vector from `trading_data.feature_01_market_regime`, designed to feed Phase 2 `SecuritySelectionModel` and Phase 3 `StrategySelectionModel`.

## Queued Tasks

- Identify global fields, helper surfaces, templates, status values, decision-record fields, model layer ids, artifact types, or ready-signal shapes that must be registered in `trading-manager`.
- Define model-facing timestamp semantics for `event_time`, `available_time`, and `tradeable_time`.
- Define the first sector/industry ETF basket, base equity universe, and sector factor-weight matrix for `SecuritySelectionModel`, with candidate-selection-parameter adjustment based on market context, trend clarity, and certainty rather than highest return.
- Decide whether `stock_etf_exposure` is model-local first or registered as a derived data kind in `trading-manager`.
- Define first label horizons and triple-barrier defaults for `TradeQualityModel`.
- Define how model-generated event standards are identified and versioned for `option_activity_event_detail`, including whether `standard_id` is separate from or derived from a model/run id and how downstream artifacts record the current standard used at event time.

## Open Gaps

- Reviewed feature-to-latent-factor evidence map for `model_01_market_regime`, including used, diagnostic/quality, evaluation-only, and intentionally unused feature keys.
- Exact first deep market-property factor formulas for `model_01_market_regime`, replacing provisional surface proxy groupings with price/trend/capital-flow/sentiment/valuation/fundamental/macro/structure/risk ontology and materially increasing reviewed evidence coverage beyond the current 132 of 1,477 generated feature keys.
- Exact persistence path for agent-reviewed promotion decisions and future active production model pointers.
- Exact artifact/manifest/ready-signal/request contract interactions for promoted/non-dry-run model evaluation artifacts.
- Exact storage path/reference requirements.
- Whether `trading-strategy` remains separate or `StrategySelectionModel` research is model-local until a later split.
- Whether `stock_etf_exposure` belongs in `trading-data` as a derived bundle output, in `trading-model` as a feature artifact, or in shared contracts after proof.
- Exact `SecuritySelectionModel` ETF/security `candidate_selection_parameter` adjustment function for candidate market parameter, trend clarity, trend persistence, certainty, and liquidity/optionability constraints.
- Exact derivation of `base_market_parameter`, `sector_weighted_market_parameter`, `candidate_market_parameter`, and unmapped-stock fallback behavior.

## Recently Accepted

- Implemented agent-backed `MarketRegimeModel` promotion review gate in `src/model_governance/agent_review.py` and `scripts/review_market_regime_promotion.py`. The script builds config/candidate rows from evaluation evidence, can invoke `openclaw agent` for a strict JSON promotion review, validates the decision, and emits a promotion decision row proposal without writing it or changing a production pointer.
- Implemented dry-run-only `MarketRegimeModel` evaluation harness in `src/model_evaluation/market_regime.py` and `scripts/evaluate_model_01_market_regime.py`. It builds in-memory governance/evaluation rows and metrics without opening a database connection, so development data cannot enter a durable SQL database by default.
- Implemented generic model governance SQL schema helpers in `src/model_governance/schema.py` and the operational wrapper `scripts/ensure_model_governance_schema.py` for dataset request/snapshot/split, evaluation label/run/metric, config version, promotion candidate, promotion decision, and rollback tables. The wrapper has a `--dry-run` SQL preview mode; default execution can create the model governance tables in the development DB. `scripts/clear_model_development_database.py` clears the `trading_model` development schema at the end of a development run with explicit confirmation. Table names are registered in `trading-manager`; concrete column registration remains deferred until the schema has been exercised with real evaluation/promotion flows.
- Accepted control-plane-facing data request boundary: use `required_data_start_time` / `required_data_end_time`; keep `label_horizons`, target symbols, train/validation/test splits, and label construction inside `trading-model` evaluation config/run tables.
- Stabilized `model_01_market_regime` factor construction: default `min_history = 20`, per-group history overrides, `std_floor`, z-score clipping, minimum signal coverage, trend bucket aggregation, and clarified commodity/rate semantics.
- Moved `model_01_market_regime` factor membership, signal directions, and reducer choices into `config/factor_specs.toml`; generator code now loads and validates config.
- Implemented `src/model_outputs/model_01_market_regime/generator.py` and `scripts/generate_model_01_market_regime.py` for the V1 continuous state-vector contract.
- Added first-party tests in `tests/test_market_regime_model.py`; default checks are compileall, unittest discovery, script `--help`, and `git diff --check`.
- Accepted Layer 1 V1 model direction: no required clustering/state labels; primary output is a continuous market-state vector keyed by `available_time`; target factor ontology should describe deep market properties rather than raw ETF-ratio proxies.

- Added `SecuritySelectionModel` / `security_selection_model` / 标的选择模型 as Layer 2 between `MarketRegimeModel` and `StrategySelectionModel`.
- Accepted canonical seven-layer names: `MarketRegimeModel`, `SecuritySelectionModel`, `StrategySelectionModel`, `TradeQualityModel`, `OptionExpressionModel`, `EventOverlayModel`, and `PortfolioRiskModel`.
- User explicitly replaced the old market-state-only repo intent with the current seven-layer model architecture.
- Added `docs/07_system_model_architecture_rfc.md` as the architecture spine.
- Updated scope/context/workflow/README to make `trading-model` the offline modeling home for all seven layers.
- Created initial `trading-model` docs spine and repository boundary.
- Added initial `.gitignore` for local environments, generated outputs, logs, and secrets.
