# Task

## Active Tasks

- Define the first implementation slice under the accepted six-layer `trading-model` scope. Recommended first slice remains Phase 1: point-in-time market-state/regime modeling, but it should be designed as Layer 1 of the full stack rather than as an isolated repo purpose.

## Queued Tasks

- Define package/source/test layout after the first implementation slice is accepted.
- Define fixture policy and default test commands.
- Identify global fields, helper surfaces, templates, status values, decision-record fields, model layer ids, artifact types, or ready-signal shapes that must be registered in `trading-main`.
- Define model-facing timestamp semantics for `event_time`, `available_time`, and `tradeable_time`.
- Define the first tradable research universe for Layer 1/2: ETF basket only, liquid equities, or both.
- Define first label horizons and triple-barrier defaults for Layer 3.
- Define how model-generated event standards are identified and versioned for `option_activity_event_detail`, including whether `standard_id` is separate from or derived from a model/run id and how downstream artifacts record the current standard used at event time.

## Open Gaps

- Exact first implementation slice.
- Exact source/package layout.
- Exact fixture and test policy.
- Exact artifact/manifest/ready-signal/request contract interactions.
- Exact storage path/reference requirements.
- Whether `trading-strategy` remains separate or Layer 2 strategy-selection research is model-local until a later split.

## Recently Accepted

- Accepted canonical model names: `MarketRegimeModel`, `StrategySelectionModel`, `TradeQualityModel`, `OptionExpressionModel`, `EventOverlayModel`, and `PortfolioRiskModel`.
- User explicitly replaced the old market-state-only repo intent with the current six-layer model architecture.
- Added `docs/07_system_model_architecture_rfc.md` as the architecture spine.
- Updated scope/context/workflow/README to make `trading-model` the offline modeling home for all six layers.
- Created initial `trading-model` docs spine and repository boundary.
- Added initial `.gitignore` for local environments, generated outputs, logs, and secrets.
