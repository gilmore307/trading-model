# src

Importable implementation code for `trading-model`.

- `model_outputs/` owns reusable model-output builders.
- `model_governance/` owns reusable SQL helpers for generic dataset request, snapshot, split, label, evaluation run, and metric tables.

Runtime scripts may import this code; `src/` must not import `scripts/`.
