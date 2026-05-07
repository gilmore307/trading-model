# Task

## Active Tasks

- Harden Layer 7 `UnderlyingActionModel` beyond the local deterministic scaffold: connect real point-in-time feature/evaluation feeds, calibrate plan-quality labels, and prove baseline improvement before any production promotion.

Layer 1-3 design, deterministic implementation scaffolds, fixture/local evidence paths, docs, and registry score naming are accepted for the current model-design phase. Layer 4 EventOverlayModel, Layer 5 AlphaConfidenceModel, and Layer 6 PositionProjectionModel have accepted V1 vector contract routes with deterministic implementation still pending; Layer 7 UnderlyingActionModel now also has a local deterministic scaffold. Real-sample promotion evidence remains a later production-readiness gap, not an active blocker for closing the accepted layer designs.

## Queued Tasks

- Implement first label horizons and confidence/EV/risk evaluation scaffold for Layer 5 `AlphaConfidenceModel`.
- Implement first target-position projection defaults for Layer 6 `PositionProjectionModel`.
- Define Layer 8 `OptionExpressionModel` after Layer 7: how the option-expression layer uses Layer 7 target/stop/holding-time/path assumptions plus market/event context for DTE, delta/moneyness, IV/vega/theta tolerance, and no-option-trade policy.
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
- Current V2.2 architecture is `MarketRegimeModel -> SectorContextModel -> TargetStateVectorModel -> EventOverlayModel -> AlphaConfidenceModel -> PositionProjectionModel -> UnderlyingActionModel -> OptionExpressionModel`, with anonymous target candidate construction inside Layer 3 preprocessing.
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
- Layer 5 is now `AlphaConfidenceModel`, consuming the reviewed Layer 1/2/3 state stack plus `event_context_vector` correction to output the final adjusted `alpha_confidence_vector` with alpha direction, strength, expected residual return, confidence, reliability, path quality, reversal risk, drawdown risk, and alpha tradability. Base/unadjusted Layer 1/2/3 alpha is diagnostic-only.
- Layer 6 is now `PositionProjectionModel`, consuming final adjusted alpha plus current/pending position, position-level friction, portfolio exposure, and risk-budget context to output `position_projection_vector`; it maps alpha to projected target holding state, not buy/sell/hold operations.
- Layer 7 is now `UnderlyingActionModel`, consuming Layer 5/6 state plus point-in-time underlying quote/liquidity/current-pending exposure/risk-policy context to output `underlying_action_plan` and `underlying_action_vector`; it maps target exposure to planned direct stock/ETF action thesis, not broker orders. Local deterministic scaffold and fixture tests are implemented in `src/models/model_07_underlying_action/`.
- `OptionExpressionModel` is now deferred to Layer 8. It should use Layer 7 underlying price-path assumptions plus option-chain evidence for option expression and contract constraints, not live execution.
- `src/models/model_01_market_regime/evidence_map.md` owns the current Layer 1 feature-to-state evidence-role contract.
- Promotion decisions can now be durably persisted through `review_market_regime_promotion.py --write-decision`; accepted approval decisions insert `model_promotion_activation` and activate the reviewed config via `model_config_version.config_status = active`, while deferred/rejected decisions leave the active config unchanged.
- MarketRegimeModel evaluation summaries now expose real metric values, explicit promotion thresholds, baseline comparison, split-stability evidence, and no-future-leak checks; the default path remains dry-run, while `evaluate_model_01_market_regime.py --from-database` performs a read-only SQL evaluation feed.
