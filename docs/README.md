# Docs

This directory is the authoritative documentation spine for `trading-model`.

## Files

- `00_scope.md` — repository boundary, in-scope work, out-of-scope work, owner intent, and re-scope signals.
- `01_context.md` — why the repository exists, related systems, environment assumptions, and dependencies.
- `02_layer_01_market_regime.md` — Layer 1 MarketRegimeModel workflow, inputs, outputs, explainability, diagnostics, and acceptance gates.
- `03_layer_02_sector_context.md` — Layer 2 SectorContextModel workflow, inputs, outputs, explainability, diagnostics, and acceptance gates.
- `04_layer_03_target_state_vector.md` — Layer 3 TargetStateVectorModel contract, anonymous target candidate preprocessing, feature blocks, labels, diagnostics, and acceptance gates.
- `05_layer_04_alpha_confidence.md` — Layer 4 AlphaConfidenceModel contract, base-alpha diagnostics policy, `alpha_confidence_vector`, labels, baselines, and boundaries.
- `06_layer_05_position_projection.md` — Layer 5 PositionProjectionModel contract, alpha-to-position boundary, `position_projection_vector`, labels, baselines, and invariants.
- `07_layer_06_underlying_action.md` — Layer 6 UnderlyingActionModel contract, direct stock/ETF planned action boundary, `underlying_action_plan` / `underlying_action_vector`, labels, baselines, and invariants.
- `08_layer_07_trading_guidance.md` — Layer 7 TradingGuidanceModel / OptionExpressionModel contract, base trading-guidance boundary, optional option-expression plan/vector, labels, baselines, and invariants.
- `09_layer_08_event_risk_governor.md` — Layer 8 EventRiskGovernor / EventIntelligenceOverlay contract, event-risk intervention status, evidence requirements, and broker-mutation boundary.
- `80_task.md` — current task state, queued work, blockers, and recently accepted work.
- `81_decision.md` — ratified repository decisions for the current route.
- `82_memory.md` — durable local continuity that does not fit narrower docs.
- `90_system_model_architecture_rfc.md` — accepted current direction-neutral model architecture and phased implementation route.
- `91_model_decomposition.md` — nine-part decomposition framework and layer-by-layer design breakdown.
- `92_vector_taxonomy.md` — accepted vocabulary for feature surfaces, feature vectors, states, state vectors, scores, diagnostics, explainability, labels, and Layer 3 preprocessing.
- `93_state_vector_feature_registry.md` — accepted semantic guardrails for Layer 1-8 score direction, quality, risk, scope, liquidity, routing, diagnostics, and research-only fields.
- `94_model_stack_closeout.md` — model-design closeout for Layers 1-8 and the no-Layer-9 boundary.
- `95_promotion_readiness.md` — production-promotion readiness matrix and evidence checklist for Layers 1-8; no production approval implied.
- `96_promotion_closeout.md` — current production-promotion closeout evidence receipt: real-evidence deferrals for Layers 1-3 and explicit production-evidence blockers for Layers 4-8; durable decisions/activation live in `trading-manager`.
- `97_historical_dataset_scope.md` — accepted distinction between broad historical training sampling universes and narrower live inference routing universes, with per-layer dataset-scope guidance.
- `98_realtime_decision_handoff.md` — model-side realtime decision input route-plan scaffold for fixture/shadow historical-model decision handoff; no production activation implied.

Layer workflow and acceptance live in the numbered layer files. The active architecture revision moves event intelligence to Layer 8 after base trading guidance. Physical implementation paths are aligned to the active conceptual layer numbering for Layers 4-8. Do not add a future model layer unless an explicit architecture revision reopens the stack; post-Layer-8 execution belongs outside `trading-model`.

Do not place generated data, artifacts, notebooks, logs, credentials, or implementation outputs in this directory.

- [99_activity_price_relationship_study.md](99_activity_price_relationship_study.md) — Cross-sectional proof study for abnormal activity versus future price/path outcomes before any EventActivityBridgeModel promotion.
- [100_event_family_scouting.md](100_event_family_scouting.md) — Layer 8 event-family scouting contract, fine-grained family batch catalog/closeout, status values, early-stop rules, and current option/news/CPI findings.
- [101_earnings_guidance_event_family_packet.md](101_earnings_guidance_event_family_packet.md) — `earnings_guidance_event_family` scouting packet, canonical source precedence, lifecycle rules, controls, labels, and early-stop gates.
- [102_event_layer_final_judgment.md](102_event_layer_final_judgment.md) — accepted event-layer go/no-go judgment: build EventRiskGovernor as bounded risk/intelligence overlay, do not promote broad event alpha or standalone option abnormality.
