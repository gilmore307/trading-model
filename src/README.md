# src

Importable implementation code for `trading-model`.

- `models/` owns model-specific implementation packages, organized one folder per accepted model output/research boundary.
- `model_governance/common/` owns shared SQL identifier, literal, database-url, and `psql` helpers.
- `model_governance/evaluation/` owns dataset/evaluation evidence schema for request, snapshot, split, label, run, and promotion metric rows.
- `model_governance/promotion/` owns model-side promotion evidence refs and agent-backed review artifacts only. Durable promotion decisions, activation, rollback, production pointers, and manager-control-plane SQL belong in `trading-manager`.

Runtime scripts may import this code; `src/` must not import `scripts/`.
