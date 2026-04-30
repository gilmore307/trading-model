# Task

## Active Tasks

- Review and refine the first `MarketRegimeModel` implementation slice: a point-in-time continuous market-state vector from `trading_derived.derived_01_market_regime`, designed to feed Phase 2 `SecuritySelectionModel` and Phase 3 `StrategySelectionModel`.

## Queued Tasks

- Identify global fields, helper surfaces, templates, status values, decision-record fields, model layer ids, artifact types, or ready-signal shapes that must be registered in `trading-main`.
- Define model-facing timestamp semantics for `event_time`, `available_time`, and `tradeable_time`.
- Define the first ETF basket and base equity universe for `SecuritySelectionModel`.
- Decide whether `stock_etf_exposure` is model-local first or registered as a derived data kind in `trading-main`.
- Define first label horizons and triple-barrier defaults for `TradeQualityModel`.
- Define how model-generated event standards are identified and versioned for `option_activity_event_detail`, including whether `standard_id` is separate from or derived from a model/run id and how downstream artifacts record the current standard used at event time.

## Open Gaps

- Exact first factor/score formulas for `model_01_market_regime`.
- Exact artifact/manifest/ready-signal/request contract interactions.
- Exact storage path/reference requirements.
- Whether `trading-strategy` remains separate or `StrategySelectionModel` research is model-local until a later split.
- Whether `stock_etf_exposure` belongs in `trading-data` as a derived bundle output, in `trading-model` as a feature artifact, or in shared contracts after proof.

## Recently Accepted

- Stabilized `model_01_market_regime` factor construction: default `min_history = 20`, per-group history overrides, `std_floor`, z-score clipping, minimum signal coverage, trend bucket aggregation, and clarified commodity/rate semantics.
- Moved `model_01_market_regime` factor membership, signal directions, and reducer choices into `config/factor_specs.toml`; generator code now loads and validates config.
- Implemented `src/model_outputs/model_01_market_regime/generator.py` and `scripts/generate_model_01_market_regime.py` for the V1 continuous state-vector contract.
- Added first-party tests in `tests/test_market_regime_model.py`; default checks are compileall, unittest discovery, script `--help`, and `git diff --check`.
- Accepted Layer 1 V1 model direction: no required clustering/state labels; primary output is a continuous market-state vector keyed by `available_time`.

- Added `SecuritySelectionModel` / `security_selection_model` / 标的选择模型 as Layer 2 between `MarketRegimeModel` and `StrategySelectionModel`.
- Accepted canonical seven-layer names: `MarketRegimeModel`, `SecuritySelectionModel`, `StrategySelectionModel`, `TradeQualityModel`, `OptionExpressionModel`, `EventOverlayModel`, and `PortfolioRiskModel`.
- User explicitly replaced the old market-state-only repo intent with the current seven-layer model architecture.
- Added `docs/07_system_model_architecture_rfc.md` as the architecture spine.
- Updated scope/context/workflow/README to make `trading-model` the offline modeling home for all seven layers.
- Created initial `trading-model` docs spine and repository boundary.
- Added initial `.gitignore` for local environments, generated outputs, logs, and secrets.
