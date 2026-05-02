# Task

## Active Tasks

- Mature Layer 1 `MarketRegimeModel` evidence and evaluation without changing its core output columns: build the feature-to-factor evidence map, define stability/usefulness evaluation, and optionally design a `market_context_state` alias/view.
- Review and refine the revised `SecuritySelectionModel` Layer 2 decomposition in `docs/08_model_decomposition.md`, especially the exact `sector_attribute_vector`, `sector_market_condition_profile`, `sector_trend_stability_vector`, holdings/exposure diagnostic boundary, and first V1 output fields.
- Complete nine-part decompositions for the remaining five model layers before expanding implementation beyond Layer 2.

## Queued Tasks

- Identify global fields, helper surfaces, templates, status values, decision-record fields, model layer ids, artifact types, or ready-signal shapes that must be registered in `trading-manager`.
- Define model-facing timestamp semantics for `event_time`, `available_time`, and `tradeable_time`.
- Define the first sector/industry ETF basket for `SecuritySelectionModel`, with sector context rows based on inferred ETF/sector attributes, market-state-conditioned trend stability, cycle regularity, rotation, trend clarity, persistence, certainty, liquidity, optionability, composition quality, and event exclusions rather than highest return, hard-coded style labels, broad-market-state scalar scoring, or premature stock selection.
- Decide whether `stock_etf_exposure` is model-local first or registered as a derived data kind in `trading-manager`.
- Define first label horizons and triple-barrier defaults for `TradeQualityModel`.
- Define how model-generated event standards are identified and versioned for `option_activity_event_detail`, including whether `standard_id` is separate from or derived from a model/run id and how downstream artifacts record the current standard used at event time.

## Open Gaps

- Reviewed feature-to-factor evidence map for `model_01_market_regime`, classifying feature families as primary evidence, diagnostic evidence, quality evidence, evaluation-only evidence, or intentionally unused evidence for each market-property factor.
- Exact mature evidence definitions for the market-property factors in `model_01_market_regime`; output columns now use price/trend/capital-flow/sentiment/valuation/fundamental/macro/structure/risk ontology, but several factors remain proxy-backed until richer point-in-time evidence is added.
- Exact Layer 1 evaluation bundle for `market_context_state` stability, Layer 2 sector trend-stability explanatory power, option-expression usefulness, and portfolio-risk usefulness.
- Whether to add a model-local `market_context_state` output view/alias around the existing factor columns for downstream readability without changing core fields.
- Exact persistence path for agent-reviewed promotion decisions and future active production model pointers.
- Exact artifact/manifest/ready-signal/request contract interactions for promoted/non-dry-run model evaluation artifacts.
- Exact storage path/reference requirements.
- Whether `trading-strategy` remains separate or `StrategySelectionModel` research is model-local until a later split.
- Whether `stock_etf_exposure` belongs in `trading-data` as a derived bundle output, in `trading-model` as a feature artifact, or in shared contracts after proof.
- Exact `SecuritySelectionModel` sector/industry parameter-surface adjustment function for market-state-conditioned trend stability, cycle regularity, rotation, trend clarity, trend persistence, certainty, composition quality, and liquidity/optionability constraints; draft decomposition exists in `docs/08_model_decomposition.md` and needs review.
- Exact path by which `MarketRegimeModel` state influences `OptionExpressionModel` contract selection and `PortfolioRiskModel` execution/risk policy without becoming a direct stock/sector ranking input.
- Exact `StrategySelectionModel` design for composing multiple strategy components into one comprehensive strategy recommendation, using anonymized target candidates plus market/sector context rather than ticker identity.

## Recently Accepted

- Chentong accepted Layer 1 as settled for V1: `MarketRegimeModel` outputs a point-in-time market-property vector from `trading_data.feature_01_market_regime`, remains unsupervised/no-clustering, and serves as broad market background rather than sector/security selection.
- Migrated `model_01_market_regime` from proxy-dashboard output columns to market-property factors: `price_behavior_factor`, `trend_certainty_factor`, `capital_flow_factor`, `sentiment_factor`, `valuation_pressure_factor`, `fundamental_strength_factor`, `macro_environment_factor`, `market_structure_factor`, and `risk_stress_factor`, plus transition pressure and data quality.
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
