# Task

## Active Tasks

1. **Layer 1 V2.2 evidence and promotion review**
   - Keep `src/models/model_01_market_regime/evidence_map.md` aligned with `config/factor_specs.toml` and the V2.2 market-tradability semantic split.
   - Review every Feature 01 addition as primary, diagnostic, quality, evaluation-only, or intentionally unused evidence.
   - Keep public outputs limited to the accepted `market_context_state` score fields: direction, direction strength, trend quality, stability, risk stress, transition risk, breadth, correlation/crowding, dispersion, liquidity pressure/support, coverage, and data quality.
   - Mature stability/usefulness evaluation for `market_context_state` against downstream baselines.

2. **Layer 3 preprocessing contract maturation**
   - Keep `src/models/model_03_target_state_vector/anonymous_target_candidate_builder/target_candidate_builder_contract.md` aligned with Layer 2 handoff and Layer 3 fitting needs.
   - Treat anonymous target candidate construction as Layer 3 preprocessing, not a separate model or peer layer.
   - Preserve the separation between model-facing `anonymous_target_feature_vector` inputs and audit/routing symbol metadata.
   - Add anonymity checks for structural bucket combinations so liquidity/cost/volatility/beta buckets do not become ticker identity surrogates.
   - Define implementation/evaluation shape before promoting any fields through `trading-manager`.

3. **Layer 3 TargetStateVectorModel contract design**
   - Review `docs/04_layer_03_target_state_vector.md` before implementation.
   - Keep Layer 3 direction evidence, tradability, transition risk, noise, liquidity/cost, and state quality separate; do not output alpha confidence or position instructions.
   - Keep retired action/variant research out of active Layer 3 work.
   - Do not promote shared Layer 3 fields or statuses through `trading-manager` until the target state-vector contract is accepted.

## Queued Tasks

- Complete nine-part decompositions for Layers 4-7.
- Define first label horizons and confidence/EV/risk defaults for `AlphaConfidenceModel`.
- Define first trading-action and target-exposure projection defaults for `TradingProjectionModel`.
- Define how `OptionExpressionModel` V1 uses market context for DTE, delta/moneyness, IV/vega/theta tolerance, and no-trade policy.
- Define event standard/version semantics for abnormal activity and event-memory evidence as overlays/inputs.
- Define final unified decision-record shape and promote it through `trading-manager` when stable.

## Open Gaps

- Real-sample promotion evidence for Layer 1 beyond fixture-scale dry runs.
- Exact downstream SQL alias/view implementation for `market_context_state`, if a physical alias is needed beyond `trading_model.model_01_market_regime`.
- Accepted production promotion for V2.2 `trading_model.model_02_sector_context` rows remains blocked by real-sample baseline/stability gates; latest review is durably deferred, not approved.
- Exact implementation/evaluation shape for producing anonymous target candidate rows.
- Exact artifact/manifest/ready-signal/request contracts for promoted model artifacts.
- Exact storage path/reference requirements for model evaluation and promotion artifacts.
- Whether legacy strategy-selection research returns later as a downstream layer or remains archived as model-local research history.

## Recently Accepted

- Layer 3 is `TargetStateVectorModel`; the active purpose is market + sector + target state-vector construction before trade/action decisions.
- Current V2.2 architecture is `MarketRegimeModel -> SectorContextModel -> TargetStateVectorModel`, with anonymous target candidate construction inside Layer 3 preprocessing, followed by Alpha/Confidence and Trading Projection layers.
- `docs/92_vector_taxonomy.md` owns the accepted distinction between feature surfaces, feature vectors, states, state vectors, scalar scores, diagnostics, explainability, and labels/outcomes.
- Layer 1 outputs only broad `market_context_state`; old market-property factor names are model-local signal groups and evidence sources, not active downstream output fields.
- Layer 1 must not pre-label ETF/sector behavior or rank sectors/ETFs/stocks.
- Layer 2 contract and deterministic implementation semantics are direction-neutral: signed sector direction is separate from trend quality, tradability, transition risk, state quality, and handoff bias.
- `src/models/model_02_sector_context/sector_context_state_contract.md` owns the current Layer 2 direction-neutral active contract, and the generator/evaluation path now emit/evaluate those fields.
- Fresh Layer 2 V2.2 rows were generated from real `feature_02_sector_context` + `model_01_market_regime` inputs, real promotion evidence was built, and a conservative review decision was persisted as deferred because baseline/stability gates did not all pass; handoff bias/absolute-path gates and leakage gates passed.
- Layer 2 does not choose final stocks in V1.
- `src/models/model_03_target_state_vector/anonymous_target_candidate_builder/target_candidate_builder_contract.md` owns the current Layer 3 preprocessing contract for anonymous candidate construction.
- `anonymous_target_feature_vector` is the Layer 3 model-facing input vector; `target_state_vector` is the Layer 3 model output.
- Model-facing target state vectors must exclude ticker/company identity.
- `OptionExpressionModel` V1 remains direct stock/ETF comparison plus long call / long put only.
- `src/models/model_01_market_regime/evidence_map.md` owns the current Layer 1 feature-to-state evidence-role contract.
- Promotion decisions can now be durably persisted through `review_market_regime_promotion.py --write-decision`; accepted approval decisions insert `model_promotion_activation` and activate the reviewed config via `model_config_version.config_status = active`, while deferred/rejected decisions leave the active config unchanged.
- MarketRegimeModel evaluation summaries now expose real metric values, explicit promotion thresholds, baseline comparison, split-stability evidence, and no-future-leak checks; the default path remains dry-run, while `evaluate_model_01_market_regime.py --from-database` performs a read-only SQL evaluation feed.
