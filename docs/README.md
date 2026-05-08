# Docs

This directory is the authoritative documentation spine for `trading-model`.

## Files

- `00_scope.md` — repository boundary, in-scope work, out-of-scope work, owner intent, and re-scope signals.
- `01_context.md` — why the repository exists, related systems, environment assumptions, and dependencies.
- `02_layer_01_market_regime.md` — Layer 1 MarketRegimeModel workflow, inputs, outputs, explainability, diagnostics, and acceptance gates.
- `03_layer_02_sector_context.md` — Layer 2 SectorContextModel workflow, inputs, outputs, explainability, diagnostics, and acceptance gates.
- `04_layer_03_target_state_vector.md` — Layer 3 TargetStateVectorModel contract, anonymous target candidate preprocessing, feature blocks, labels, diagnostics, and acceptance gates.
- `05_layer_04_event_overlay.md` — Layer 4 EventOverlayModel contract and V1 `event_context_vector` shape, score families, labels, baselines, and boundaries.
- `06_layer_05_alpha_confidence.md` — Layer 5 AlphaConfidenceModel contract, base-alpha diagnostics policy, adjusted `alpha_confidence_vector`, labels, baselines, and boundaries.
- `07_layer_06_position_projection.md` — Layer 6 PositionProjectionModel contract, alpha-to-position boundary, `position_projection_vector`, labels, baselines, and invariants.
- `08_layer_07_underlying_action.md` — Layer 7 UnderlyingActionModel contract, direct stock/ETF planned action boundary, `underlying_action_plan` / `underlying_action_vector`, labels, baselines, and invariants.
- `09_layer_08_option_expression.md` — Layer 8 OptionExpressionModel contract, option-expression boundary, `option_expression_plan` / `expression_vector`, contract-fit scoring, labels, baselines, and invariants.
- `80_task.md` — current task state, queued work, blockers, and recently accepted work.
- `81_decision.md` — ratified repository decisions for the current route.
- `82_memory.md` — durable local continuity that does not fit narrower docs.
- `90_system_model_architecture_rfc.md` — accepted current direction-neutral model architecture and phased implementation route.
- `91_model_decomposition.md` — nine-part decomposition framework and layer-by-layer design breakdown.
- `92_vector_taxonomy.md` — accepted vocabulary for feature surfaces, feature vectors, states, state vectors, scores, diagnostics, explainability, labels, and Layer 3 preprocessing.
- `93_state_vector_feature_registry.md` — accepted semantic guardrails for Layer 1-8 score direction, quality, risk, scope, liquidity, routing, diagnostics, and research-only fields.
- `94_model_stack_closeout.md` — model-design closeout for Layers 1-8 and the no-Layer-9 boundary.
- `95_promotion_readiness.md` — production-promotion readiness matrix and evidence checklist for Layers 1-8; no production approval implied.
- `96_promotion_closeout.md` — current production-promotion closeout receipt: persisted real-evidence deferred decisions for Layers 1-3 and explicit production-evidence blockers for Layers 4-8.

Layer workflow and acceptance live in the numbered layer files. Do not add a future model layer unless an explicit architecture revision reopens the stack; post-Layer-8 execution belongs outside `trading-model`.

Do not place generated data, artifacts, notebooks, logs, credentials, or implementation outputs in this directory.
