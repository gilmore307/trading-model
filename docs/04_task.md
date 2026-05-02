# Task

## Active Tasks

1. **Layer 1 evidence maturation**
   - Keep `src/models/model_01_market_regime/evidence_map.md` aligned with `config/factor_specs.toml`.
   - Review every Feature 01 addition as primary, diagnostic, quality, evaluation-only, or intentionally unused evidence.
   - Mature stability/usefulness evaluation for `market_context_state` against downstream baselines.

2. **Layer 2 contract refinement**
   - Keep `src/models/model_02_security_selection/sector_context_state_contract.md` aligned with implementation.
   - Keep ETF/sector attributes inferred from evidence.
   - Keep `stock_etf_exposure` as downstream candidate-construction evidence, not Layer 2 core behavior modeling.

## Queued Tasks

- Define the anonymous target candidate builder contract:
  - `target_candidate_id`;
  - `anonymous_target_feature_vector`;
  - audit/routing symbol metadata boundary.
- Complete nine-part decompositions for Layers 3-7.
- Define first label horizons and triple-barrier defaults for `TradeQualityModel`.
- Define how `OptionExpressionModel` V1 uses market context for DTE, delta/moneyness, IV/vega/theta tolerance, and no-trade policy.
- Define event standard/version semantics for `EventOverlayModel` abnormal activity and event-memory outputs.
- Define final unified decision-record shape and promote it through `trading-manager` when stable.

## Open Gaps

- Exact mature evidence definitions for each Layer 1 factor beyond the current V1 family-level map.
- Exact `market_context_state` alias/view implementation, if any.
- Exact implementation/evaluation shape for producing `trading_model.model_02_security_selection` rows.
- Exact persistence path for promotion decisions and future active production model pointers.
- Exact artifact/manifest/ready-signal/request contracts for promoted model artifacts.
- Exact storage path/reference requirements for model evaluation and promotion artifacts.
- Whether `trading-strategy` remains separate or Layer 3 strategy-selection research stays model-local until a later split.

## Recently Accepted

- Current architecture is `MarketRegimeModel -> SecuritySelectionModel -> anonymous target candidate builder + StrategySelectionModel -> TradeQualityModel -> OptionExpressionModel -> EventOverlayModel -> PortfolioRiskModel`.
- Layer 1 outputs only broad `market_context_state` from current market-property factors.
- Layer 1 must not pre-label ETF/sector behavior or rank sectors/ETFs/stocks.
- Layer 2 outputs sector/industry trend-stability and inferred basket attributes as `sector_context_state`.
- `src/models/model_02_security_selection/sector_context_state_contract.md` owns the current Layer 2 V1 field contract.
- Layer 2 does not choose final stocks in V1.
- Target-aware fitting starts downstream through anonymous target candidates.
- Model-facing target vectors must exclude ticker/company identity.
- `OptionExpressionModel` V1 remains direct stock/ETF comparison plus long call / long put only.
- `src/models/model_01_market_regime/evidence_map.md` owns the current Layer 1 feature-to-factor evidence-role contract.
