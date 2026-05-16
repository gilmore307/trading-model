# Task

## Active Tasks

- Promote-first model phase: concentrate current modeling effort on producing the first usable production-promotable model version. Start with Layer 1 `MarketRegimeModel` promotion-gate repair/evidence production because Layer 2 and Layer 3 depend on a stable approved Layer 1 foundation.

Layers 1-8 are structurally closed for the accepted local deterministic scaffold phase; see `docs/94_model_stack_closeout.md`. Realtime decision handoff scaffolds remain accepted but are parked until at least one model has an approved/promotable version. The next work is historical evidence production, gate repair, calibration/baseline/stability/leakage evidence, and manager-side promotion review preparation — not realtime integration expansion or additional ad hoc repository cleanup.

## Historical-Training Evidence Requirements

These are run/evidence requirements for promotion readiness, not open model-design work items:

- Layer 1 and Layer 2 require remediated real-data evidence before any promotion approval can be considered.
- Layer 3 requires upstream Layer 1/2 production approval or an explicitly reviewed offline-evidence exception, plus Layer 3 calibration evidence.
- Layers 4-8 require point-in-time datasets, labels, real evaluation metrics, baseline/stability/leakage/calibration evidence, and manager-side `model_promotion_review` requests.
- Missing evidence or failed gates must remain deferred/rejected and must not create activation records or move production pointers.

## Not Current Historical-Training Scope

These items are intentionally outside the current promote-first historical-training run and must not be treated as active repository work items:

- realtime data/monitoring or live/shadow integration expansion before a model has an approved/promotable version;
- broker/order/fill/account lifecycle;
- production model activation without approved manager-side review decisions;
- exact execution-owned unified decision-record artifacts beyond the current risk-cap invariant;
- additional durable manager/storage interface ownership inside `trading-model`.

## Recently Accepted

- Added `model_realtime_decision_route_plan` and validation scaffold for `execution_model_decision_input_snapshot` handoff from `trading-execution`. It maps Layer 1-8 input refs to reviewed generator entrypoints for fixture/shadow historical-model decision routing without running models, activating configs, constructing orders, or persisting manager decisions.
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

## Event-layer research closeout — 2026-05-15

The abnormal-activity, option-direction, matched-control, raw-news, and canonical earnings/guidance scouting slice is closed for the current judgment pass.

Accepted judgment: build/keep Layer 8 as a bounded EventRiskGovernor / EventIntelligenceOverlay, not as broad event alpha or standalone option abnormality. See `docs/102_event_layer_final_judgment.md`.

First itemized follow-up completed: `/root/projects/trading-model/storage/earnings_guidance_event_alone_q4_2025_20260515/` tested 12 Q4 2025 canonical Nasdaq earnings shells against 36 same-symbol non-earnings controls. It showed direction-neutral path expansion, not directional alpha; earnings/guidance remains `scouting`.

Second itemized follow-up completed: `/root/projects/trading-model/storage/earnings_guidance_result_artifact_scout_q4_2025_20260515/` joined those shells to official SEC result artifacts. It found official result artifacts for all 12 events and partial XBRL metric-direction interpretation for 11 events, but no guidance interpretation and no signed-alpha proof.

Remaining future work is evidence expansion only: more earnings seasons, official company release/exhibit/transcript guidance interpretations, verified no-option-abnormality controls, and family-specific promotion gates before any `pilot_training` status.

Third itemized follow-up completed: `/root/projects/trading-model/storage/earnings_option_abnormality_split_scout_20260515/` joined canonical 2026 earnings shells to the reviewed option matrix and found 2 option-covered earnings rows, both abnormal, with 0 verified earnings-without-option-abnormality controls. The earnings+option amplifier comparison remains blocked until matched no-option-abnormality controls are acquired or verified.

Fourth itemized follow-up completed: `/root/projects/trading-model/storage/earnings_option_no_abnormality_control_probe_20260515/` sampled remaining canonical earnings rows for no-option-abnormality controls under the same option-event standard. Result: 0 verified no sampled option-abnormality controls; 8/8 newly probed rows emitted option abnormality on successful sampled contracts, with PFE/RKLB partial coverage from ThetaData HTTP 472. The earnings+option amplifier comparison remains blocked.

Sixth itemized follow-up completed: `/root/projects/trading-model/storage/option_abnormality_non_earnings_saturation_20260515/` showed the current option-event standard is saturated. The reviewed matrix had 34 same-symbol non-earnings symbol/date windows, and all 34 emitted complete option-abnormality events. This explains the lack of clean earnings-without-option-abnormality controls and blocks further amplifier testing under the current standard.

Seventh itemized follow-up completed: `/root/projects/trading-model/storage/earnings_guidance_readiness_scout_q4_2025_20260515/` audited official-guidance readiness. Result: 12/12 official result artifacts, 11 partial result-context rows, 0 official guidance interpretations, 0 expectation baselines, and 0 signed-direction-ready rows. Earnings/guidance remains direction-neutral event-risk scouting only.

Eighth itemized follow-up completed: `/root/projects/trading-model/storage/earnings_guidance_artifact_coverage_scout_q4_2025_20260515/` audited local official-document coverage. Result: 12/12 SEC result filing references, 0 local official filing/release/transcript text artifacts, 0 accepted guidance interpretations, 0 expectation baselines, and 0 signed-direction-ready rows. Earnings/guidance remains direction-neutral EventRiskGovernor context until official document text, guidance interpretation, and expectation baselines exist.

Ninth itemized follow-up completed: `/root/projects/trading-model/storage/earnings_guidance_artifact_coverage_with_documents_q4_2025_20260515/` reran the official-artifact coverage gate after bounded SEC document-text acquisition. Result: 12/12 official filing document text artifacts acquired and visible to the coverage gate, 0 accepted guidance interpretations, 0 expectation baselines, and 0 signed-direction-ready rows. The local-document blocker is resolved; the interpretation/expectation blocker remains.
