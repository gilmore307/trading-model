# src

Importable implementation code for `trading-model`.

- `model_outputs/` owns reusable model-output builders.
- `model_governance/` owns reusable SQL helpers and row builders for generic dataset request, snapshot, split, label, evaluation run, metric, config version, promotion candidate, promotion decision, rollback, and agent-backed promotion review surfaces.
- `model_evaluation/` owns dry-run evaluation harnesses that build governance/evaluation rows without touching durable databases.

Runtime scripts may import this code; `src/` must not import `scripts/`.
