# Task

## Active Tasks

- None for the historical-data training preparation boundary.

Layers 1-8 are structurally closed for the accepted local deterministic scaffold phase; see `docs/94_model_stack_closeout.md`. The model-side realtime decision handoff scaffold is now present for fixture/shadow routing from execution realtime feature snapshots into historical-model decision inputs; see `docs/98_realtime_decision_handoff.md`. The next work is evidence production during formal historical-training runs or explicitly approved live/shadow integration, not additional ad hoc repository work item cleanup.

## Historical-Training Evidence Requirements

These are run/evidence requirements for promotion readiness, not open model-design work items:

- Layer 1 and Layer 2 require remediated real-data evidence before any promotion approval can be considered.
- Layer 3 requires upstream Layer 1/2 production approval or an explicitly reviewed offline-evidence exception, plus Layer 3 calibration evidence.
- Layers 4-8 require point-in-time datasets, labels, real evaluation metrics, baseline/stability/leakage/calibration evidence, and manager-side `model_promotion_review_v1` requests.
- Missing evidence or failed gates must remain deferred/rejected and must not create activation records or move production pointers.

## Not Current Historical-Training Scope

These items are intentionally outside the current no-broker historical-training run and must not be treated as active repository work items:

- broker/order/fill/account lifecycle;
- production model activation without approved manager-side review decisions;
- exact execution-owned unified decision-record artifacts beyond the current risk-cap invariant;
- additional durable manager/storage interface ownership inside `trading-model`.

## Recently Accepted

- Added `model_realtime_decision_route_plan_v1` and validation scaffold for `execution_model_decision_input_snapshot_v1` handoff from `trading-execution`. It maps Layer 1-8 input refs to reviewed generator entrypoints for fixture/shadow historical-model decision routing without running models, activating configs, constructing orders, or persisting manager decisions.
- Promotion closeout evidence is recorded in `docs/96_promotion_closeout.md`: Layers 1-2 have real database evidence; Layers 3-8 have blocked/deferred eval evidence proving no production eval substrate exists yet. No production activation occurred, and durable decision/activation ownership is now in `trading-manager`.
- Production-promotion readiness rules are accepted for Layers 1-8 in `docs/95_promotion_readiness.md`: every production approval requires dataset snapshot/split/labels/eval run/metrics/candidate/thresholds/baselines/stability/leakage/calibration/decision evidence. Current status remains deferred, not production-approved.
- Repository model-stack closeout is accepted for the current design phase: Layers 1-8 now have accepted contracts, docs, local deterministic scaffolds/evaluation helpers where in scope, registry score naming, and fixture evidence. There is no accepted Layer 9 inside `trading-model`; post-Layer-8 execution remains outside this repository.
- Layer 1-3 model-design closeout is accepted for the current phase: MarketRegimeModel, SectorContextModel, and TargetStateVectorModel have reviewed contracts, deterministic local implementations/evaluation scaffolds, docs, and registry core-score naming. Production promotion remains deferred until real-sample gates pass.
- Layer 3 is `TargetStateVectorModel`; the active purpose is market + sector + target state-vector construction before trade/action decisions.
- Current V2.2 architecture is `MarketRegimeModel -> SectorContextModel -> TargetStateVectorModel -> EventOverlayModel -> AlphaConfidenceModel -> PositionProjectionModel -> UnderlyingActionModel -> OptionExpressionModel`, with anonymous target candidate construction inside Layer 3 preprocessing.
- Layer 8 is now `OptionExpressionModel`, consuming Layer 7 underlying price-path assumptions plus option-chain evidence to output offline `option_expression_plan` / `expression_vector` rows. Local deterministic scaffold and fixture tests are implemented in `src/models/model_08_option_expression/`. Accepted historical bucket defaults are near-to-far listed expirations, current-to-target strike corridor plus three listed strike levels on both sides, no acquisition-time prefilter for extreme/illiquid contracts during model construction, and V1 single-leg expressions only.
- `docs/92_vector_taxonomy.md` owns the accepted distinction between feature surfaces, feature vectors, states, state vectors, scalar scores, diagnostics, explainability, and labels/outcomes.
- Layer 1 outputs only broad `market_context_state`; old market-property factor names are model-local signal groups and evidence sources, not active downstream output fields.
- Layer 1 must not pre-label ETF/sector behavior or rank sectors/ETFs/stocks.
- Layer 2 contract and deterministic implementation semantics are direction-neutral: signed sector direction is separate from trend quality, tradability, transition risk, state quality, and handoff bias.
- `src/models/model_02_sector_context/sector_context_state_contract.md` owns the current Layer 2 direction-neutral active contract, and the generator/evaluation path now emit/evaluate those fields.
- Fresh Layer 2 V2.2 rows were generated from real `feature_02_sector_context` + `model_01_market_regime` inputs, real promotion evidence was built, and the conservative review outcome remained deferred because baseline/stability gates did not all pass; handoff bias/absolute-path gates and leakage gates passed.
- Layer 2 does not choose final stocks in V1.
- `src/models/model_03_target_state_vector/anonymous_target_candidate_builder/target_candidate_builder_contract.md` owns the current Layer 3 preprocessing contract for anonymous candidate construction.
- `src/models/model_03_target_state_vector/anonymous_target_candidate_builder/builder.py` implements anonymous candidate rows and identity-safety checks for `anonymous_target_feature_vector`.
- `src/models/model_03_target_state_vector/generator.py` implements deterministic `model_03_target_state_vector` rows from `feature_03_target_state_vector` blocks with signed direction separated from tradability, transition/noise risk, liquidity, and state quality.
- `src/models/model_03_target_state_vector/evaluation.py` and `scripts/models/model_03_target_state_vector/` implement the Layer 3 baseline-ladder evidence path; fixture/local review must defer until real-data gates pass.
- `anonymous_target_feature_vector` is the Layer 3 model-facing input vector; `target_context_state` is the Layer 3 conceptual model output.
- Model-facing target context/state vectors must exclude ticker/company identity.
- Layer 4 is now `EventOverlayModel`, consuming point-in-time event evidence from `source_04_event_overlay`, event detail artifacts, upstream `market_context_state` / `sector_context_state` / `target_context_state` references, and scope/sensitivity metadata to output `event_context_vector`. Local deterministic scaffold and fixture tests are implemented in `src/models/model_04_event_overlay/`. `price_action` events such as false breakouts and liquidity sweeps are accepted inside this layer, not as a new model layer.
- Layer 5 is now `AlphaConfidenceModel`, consuming the reviewed Layer 1/2/3 state stack plus `event_context_vector` correction to output the final adjusted `alpha_confidence_vector` with alpha direction, strength, expected residual return, confidence, reliability, path quality, reversal risk, drawdown risk, and alpha tradability. Base/unadjusted Layer 1/2/3 alpha is diagnostic-only. Local deterministic scaffold and fixture tests are implemented in `src/models/model_05_alpha_confidence/`.
- Layer 6 is now `PositionProjectionModel`, consuming final adjusted alpha plus current/pending position, position-level friction, portfolio exposure, and risk-budget context to output `position_projection_vector`; it maps alpha to projected target holding state, not buy/sell/hold operations. Local deterministic scaffold and fixture tests are implemented in `src/models/model_06_position_projection/`.
- Layer 7 is now `UnderlyingActionModel`, consuming Layer 5/6 state plus point-in-time underlying quote/liquidity/current-pending exposure/risk-policy context to output `underlying_action_plan` and `underlying_action_vector`; it maps target exposure to planned direct stock/ETF action thesis, not broker orders. Local deterministic scaffold and fixture tests are implemented in `src/models/model_07_underlying_action/`.
- `OptionExpressionModel` is Layer 8. It uses Layer 7 underlying price-path assumptions plus option-chain evidence for option expression and contract constraints, not live execution.
- `src/models/model_01_market_regime/evidence_map.md` owns the current Layer 1 feature-to-state evidence-role contract.
- Promotion review scripts now emit model-side evidence/review artifacts only and may classify artifact retention intent. Durable promotion requests, lifecycle scheduling, decisions, activation records, rollbacks, and production pointers are manager-control-plane work owned by `trading-manager`; storage physical lifecycle execution remains `trading-storage`-owned.
- MarketRegimeModel evaluation summaries now expose real metric values, explicit promotion thresholds, baseline comparison, split-stability evidence, and no-future-leak checks; the default path remains dry-run, while `evaluate_model_01_market_regime.py --from-database` performs a read-only SQL evaluation feed.
