# Task

## Active Tasks

- Continue Layer 5 `AlphaConfidenceModel` after the accepted design route: define deterministic label/evaluation scaffolding and first confidence-calibration evidence path.

Layer 1-3 design, deterministic implementation scaffolds, fixture/local evidence paths, docs, and registry score naming are accepted for the current model-design phase. Layer 4 EventOverlayModel and Layer 5 AlphaConfidenceModel now have accepted V1 vector contract routes; deterministic implementation remains pending. Real-sample promotion evidence remains a later production-readiness gap, not an active blocker for closing the accepted layer designs.

## Queued Tasks

- Complete nine-part decompositions for Layers 6-7 after the Layer 5 confidence route.
- Implement first label horizons and confidence/EV/risk evaluation scaffold for Layer 5 `AlphaConfidenceModel`.
- Define first trading-action and target-exposure projection defaults for Layer 6 `TradingProjectionModel`.
- Define how Layer 7 expression/final-action work uses market/event context for DTE, delta/moneyness, IV/vega/theta tolerance, and no-trade policy.
- Implement Layer 4 deterministic EventEncoder / EventContextMatcher / EventOverlayScorer scaffold after the accepted event-context vector contract.
- Define final unified decision-record shape and promote it through `trading-manager` when stable.

## Open Gaps

- Real-sample promotion evidence for Layer 1 beyond fixture-scale dry runs.
- Exact downstream SQL alias/view implementation for `market_context_state`, if a physical alias is needed beyond `trading_model.model_01_market_regime`.
- Accepted production promotion for V2.2 `trading_model.model_02_sector_context` rows remains blocked by real-sample baseline/stability gates; latest review is durably deferred, not approved.
- Production-scale Layer 3 real-data evidence and accepted promotion decision for `model_03_target_state_vector`.
- Whether legacy strategy-selection research returns later as a downstream layer or remains archived as model-local research history.

These are promotion/production-readiness gaps. They do not reopen the accepted Layer 1-3 model contracts for the current design phase.

## Deferred Until Manager Phase

- Exact artifact/manifest/ready-signal/request contracts for promoted model artifacts.
- Exact storage path/reference requirements for model evaluation and promotion artifacts.
- These shared contracts stay deferred until all model layers are designed and the `trading-manager` development phase begins; model work should continue with local/offline evidence and avoid prematurely registering durable manager/storage interfaces.

## Recently Accepted

- Layer 1-3 model-design closeout is accepted for the current phase: MarketRegimeModel, SectorContextModel, and TargetStateVectorModel have reviewed contracts, deterministic local implementations/evaluation scaffolds, docs, and registry core-score naming. Production promotion remains deferred until real-sample gates pass.
- Layer 3 is `TargetStateVectorModel`; the active purpose is market + sector + target state-vector construction before trade/action decisions.
- Current V2.2 architecture is `MarketRegimeModel -> SectorContextModel -> TargetStateVectorModel -> EventOverlayModel -> AlphaConfidenceModel -> TradingProjectionModel -> expression/final-action boundary`, with anonymous target candidate construction inside Layer 3 preprocessing.
- `docs/92_vector_taxonomy.md` owns the accepted distinction between feature surfaces, feature vectors, states, state vectors, scalar scores, diagnostics, explainability, and labels/outcomes.
- Layer 1 outputs only broad `market_context_state`; old market-property factor names are model-local signal groups and evidence sources, not active downstream output fields.
- Layer 1 must not pre-label ETF/sector behavior or rank sectors/ETFs/stocks.
- Layer 2 contract and deterministic implementation semantics are direction-neutral: signed sector direction is separate from trend quality, tradability, transition risk, state quality, and handoff bias.
- `src/models/model_02_sector_context/sector_context_state_contract.md` owns the current Layer 2 direction-neutral active contract, and the generator/evaluation path now emit/evaluate those fields.
- Fresh Layer 2 V2.2 rows were generated from real `feature_02_sector_context` + `model_01_market_regime` inputs, real promotion evidence was built, and a conservative review decision was persisted as deferred because baseline/stability gates did not all pass; handoff bias/absolute-path gates and leakage gates passed.
- Layer 2 does not choose final stocks in V1.
- `src/models/model_03_target_state_vector/anonymous_target_candidate_builder/target_candidate_builder_contract.md` owns the current Layer 3 preprocessing contract for anonymous candidate construction.
- `src/models/model_03_target_state_vector/anonymous_target_candidate_builder/builder.py` implements anonymous candidate rows and identity-safety checks for `anonymous_target_feature_vector`.
- `src/models/model_03_target_state_vector/generator.py` implements deterministic `model_03_target_state_vector` rows from `feature_03_target_state_vector` blocks with signed direction separated from tradability, transition/noise risk, liquidity, and state quality.
- `src/models/model_03_target_state_vector/evaluation.py` and `scripts/models/model_03_target_state_vector/` implement the Layer 3 baseline-ladder evidence path; fixture/local review must defer until real-data gates pass.
- `anonymous_target_feature_vector` is the Layer 3 model-facing input vector; `target_context_state` is the Layer 3 conceptual model output.
- Model-facing target context/state vectors must exclude ticker/company identity.
- Layer 4 is now `EventOverlayModel`, consuming point-in-time event evidence from `source_04_event_overlay`, event detail artifacts, upstream `market_context_state` / `sector_context_state` / `target_context_state` references, and scope/sensitivity metadata to output `event_context_vector`.
- Layer 5 is now `AlphaConfidenceModel`, consuming `target_context_state` plus `event_context_vector` to output `alpha_confidence_vector` with calibrated direction confidence, expected return/value, risk, uncertainty, event adjustment, context support, and calibration quality.
- `OptionExpressionModel` V1 remains direct stock/ETF comparison plus long call / long put only, now inside the Layer 7 expression/final-action boundary.
- `src/models/model_01_market_regime/evidence_map.md` owns the current Layer 1 feature-to-state evidence-role contract.
- Promotion decisions can now be durably persisted through `review_market_regime_promotion.py --write-decision`; accepted approval decisions insert `model_promotion_activation` and activate the reviewed config via `model_config_version.config_status = active`, while deferred/rejected decisions leave the active config unchanged.
- MarketRegimeModel evaluation summaries now expose real metric values, explicit promotion thresholds, baseline comparison, split-stability evidence, and no-future-leak checks; the default path remains dry-run, while `evaluate_model_01_market_regime.py --from-database` performs a read-only SQL evaluation feed.
