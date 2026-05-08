# Docs

This directory is the authoritative documentation spine for `trading-model`.

## Files

- `00_scope.md` — repository boundary, in-scope work, out-of-scope work, and owner intent.
- `01_context.md` — why the repository exists, related systems, environment assumptions, and dependencies.
- `02_layer_01_market_regime.md` — Layer 1 workflow, inputs, outputs, explainability, diagnostics, and acceptance gates.
- `03_layer_02_sector_context.md` — Layer 2 workflow, inputs, outputs, explainability, diagnostics, and acceptance gates.
- `04_layer_03_target_state_vector.md` — accepted Layer 3 target-context/state-vector contract, deterministic scaffold status, market/sector/target feature blocks, labels, diagnostics, and acceptance gates.
- `05_layer_04_event_overlay.md` — accepted Layer 4 EventOverlayModel design route and V1 `event_context_vector` shape, core score families, labels, baselines, and boundaries.
- `06_layer_05_alpha_confidence.md` — accepted Layer 5 AlphaConfidenceModel design route, base/unadjusted diagnostics policy, final adjusted 9×4 `alpha_confidence_vector` shape, labels, baselines, and boundaries.
- `07_layer_06_position_projection.md` — accepted Layer 6 PositionProjectionModel design route, alpha-to-position projection boundary, V1 `position_projection_vector` score families, handoff summary, labels, baselines, and invariants.
- `08_layer_07_underlying_action.md` — accepted Layer 7 UnderlyingActionModel design route, direct stock/ETF planned action boundary, V1 `underlying_action_plan`/`underlying_action_vector` shape, entry/target/stop/time thesis, labels, baselines, and invariants.
- `09_layer_08_option_expression.md` — accepted Layer 8 OptionExpressionModel design route, option-expression boundary, V1 `option_expression_plan`/`expression_vector` shape, contract-fit scoring, labels, baselines, and invariants.
- `80_task.md` — current task state, queued work, blockers, and recently accepted work.
- `81_decision.md` — ratified repository decisions.
- `82_memory.md` — durable local continuity that does not fit narrower docs.
- `90_system_model_architecture_rfc.md` — accepted current direction-neutral model architecture and phased implementation route.
- `91_model_decomposition.md` — current nine-part model decomposition framework and layer-by-layer design breakdown.
- `92_vector_taxonomy.md` — accepted vocabulary for feature surfaces, feature vectors, states, state vectors, scores, diagnostics, explainability, labels, and Layer 3 preprocessing.
- `93_state_vector_feature_registry.md` — accepted semantic guardrails for Layer 1/2/3 state-vector, Layer 4 event-context, Layer 5 alpha-confidence, Layer 6 position-projection, Layer 7 underlying-action, and Layer 8 option-expression score direction, quality, risk, scope, liquidity, routing, diagnostics, and research-only fields.
- `94_model_stack_closeout.md` — accepted repository closeout for the Layers 1-8 model-design phase, no-Layer-9 boundary, remaining production-hardening work, and verification receipt.

Layer workflow and acceptance live in the numbered layer files. Do not add a future model layer unless an explicit architecture revision reopens the stack; post-Layer-8 execution belongs outside `trading-model`.

Do not place generated data, artifacts, notebooks, logs, credentials, or implementation outputs in this directory.
