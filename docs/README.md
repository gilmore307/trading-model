# Docs

This directory is the authoritative documentation spine for `trading-model`.

## Files

- `00_scope.md` — repository boundary, in-scope work, out-of-scope work, and owner intent.
- `01_context.md` — why the repository exists, related systems, environment assumptions, and dependencies.
- `02_layer_01_market_regime.md` — Layer 1 workflow, inputs, outputs, explainability, diagnostics, and acceptance gates.
- `03_layer_02_sector_context.md` — Layer 2 workflow, inputs, outputs, explainability, diagnostics, and acceptance gates.
- `04_layer_03_target_state_vector.md` — draft Layer 3 target state-vector contract, market/sector/target feature blocks, labels, diagnostics, and acceptance gates.
- `80_task.md` — current task state, queued work, blockers, and recently accepted work.
- `81_decision.md` — ratified repository decisions.
- `82_memory.md` — durable local continuity that does not fit narrower docs.
- `90_system_model_architecture_rfc.md` — accepted current direction-neutral model architecture and phased implementation route.
- `91_model_decomposition.md` — current nine-part model decomposition framework and layer-by-layer design breakdown.
- `92_vector_taxonomy.md` — accepted vocabulary for feature surfaces, feature vectors, states, state vectors, scores, diagnostics, explainability, labels, and Layer 3 preprocessing.

Layer workflow and acceptance live in the numbered layer files. Add future layers as `04_layer_03_...`, `05_layer_04_...`, and so on before adding broad workflow prose.

Do not place generated data, artifacts, notebooks, logs, credentials, or implementation outputs in this directory.
