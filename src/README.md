# src

Importable implementation code for `trading-model`.

- `models/` owns model-specific implementation packages, organized one folder per accepted model output/research boundary.
- `model_governance/` owns reusable SQL helpers, persistence SQL renderers, and row builders for generic dataset request, snapshot, split, label, evaluation run, metric, config version, promotion candidate, promotion decision, rollback, and agent-backed promotion review surfaces. Accepted promotion activation is represented by the active `model_config_version` row; deferred or rejected decisions leave that status unchanged.

Runtime scripts may import this code; `src/` must not import `scripts/`.
