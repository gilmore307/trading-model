# Task

## Active Tasks

1. **Layer 1 evidence maturation**
   - Keep `src/models/model_01_market_regime/evidence_map.md` aligned with `config/factor_specs.toml`.
   - Review every Feature 01 addition as primary, diagnostic, quality, evaluation-only, or intentionally unused evidence.
   - Mature stability/usefulness evaluation for `market_context_state` against downstream baselines.

2. **Layer 2 contract refinement**
   - Keep `src/models/model_02_sector_context/sector_context_state_contract.md` aligned with implementation.
   - Keep ETF/sector attributes inferred from evidence.
   - Keep `stock_etf_exposure` as downstream candidate-construction evidence, not Layer 2 core behavior modeling.

3. **Layer 3 anonymous target candidate builder contract maturation**
   - Keep `src/models/model_03_target_state_vector/anonymous_target_candidate_builder/target_candidate_builder_contract.md` aligned with Layer 2 handoff and Layer 3 fitting needs.
   - Preserve the separation between model-facing anonymous vectors and audit/routing symbol metadata.
   - Define implementation/evaluation shape before promoting any fields through `trading-manager`.

4. **Layer 3 TargetStateVectorModel contract design**
   - Review `docs/04_layer_03_target_state_vector.md` before implementation.
   - Freeze the old strategy-family/variant taxonomy as legacy research; do not expand it as active Layer 3 work.
   - Do not promote shared Layer 3 fields or statuses through `trading-manager` until the target state-vector contract is accepted.

## Queued Tasks

- Complete nine-part decompositions for Layers 4-7.
- Define first label horizons and triple-barrier defaults for `TradeQualityModel`.
- Define how `OptionExpressionModel` V1 uses market context for DTE, delta/moneyness, IV/vega/theta tolerance, and no-trade policy.
- Define event standard/version semantics for `EventOverlayModel` abnormal activity and event-memory outputs.
- Define final unified decision-record shape and promote it through `trading-manager` when stable.

## Open Gaps

- Exact mature evidence definitions for each Layer 1 factor beyond the current V1 family-level map.
- Exact `market_context_state` alias/view implementation, if any.
- Exact implementation/evaluation shape for producing `trading_model.model_02_sector_context` rows.
- Exact implementation/evaluation shape for producing anonymous target candidate rows.
- Exact artifact/manifest/ready-signal/request contracts for promoted model artifacts.
- Exact storage path/reference requirements for model evaluation and promotion artifacts.
- Whether legacy strategy-selection research returns later as a downstream layer or remains archived as model-local research history.

## Recently Accepted

- Layer 3 has been reset from strategy-family/variant selection to `TargetStateVectorModel`; the active purpose is market + sector + target state-vector construction before trade/strategy decisions.
- Current architecture is `MarketRegimeModel -> SectorContextModel -> anonymous target candidate builder + TargetStateVectorModel -> TradeQualityModel -> OptionExpressionModel -> EventOverlayModel -> PortfolioRiskModel`.
- Layer 1 outputs only broad `market_context_state` from current market-property factors.
- Layer 1 must not pre-label ETF/sector behavior or rank sectors/ETFs/stocks.
- Layer 2 outputs sector/industry trend-stability and inferred basket attributes as `sector_context_state`.
- `src/models/model_02_sector_context/sector_context_state_contract.md` owns the current Layer 2 V1 field contract.
- Layer 2 does not choose final stocks in V1.
- `src/models/model_03_target_state_vector/anonymous_target_candidate_builder/target_candidate_builder_contract.md` owns the current anonymous candidate-builder V1 contract.
- Target-state fitting starts downstream through anonymous target candidates.
- Model-facing target state vectors must exclude ticker/company identity.
- `OptionExpressionModel` V1 remains direct stock/ETF comparison plus long call / long put only.
- `src/models/model_01_market_regime/evidence_map.md` owns the current Layer 1 feature-to-factor evidence-role contract.
- Promotion decisions can now be durably persisted through `review_market_regime_promotion.py --write-decision`; accepted approval decisions insert `model_promotion_activation` and activate the reviewed config via `model_config_version.config_status = active`, while deferred/rejected decisions leave the active config unchanged.
- MarketRegimeModel evaluation summaries now expose real metric values, explicit promotion thresholds, baseline comparison, split-stability evidence, and no-future-leak checks; the default path remains dry-run, while `evaluate_model_01_market_regime.py --from-database` performs a read-only SQL evaluation feed.
