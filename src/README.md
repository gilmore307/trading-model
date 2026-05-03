# src

Importable implementation code for `trading-model`.

- `models/` owns model-specific implementation packages, organized one folder per accepted model output/research boundary.
- `model_governance/common/` owns shared SQL identifier, literal, database-url, and `psql` helpers.
- `model_governance/evaluation/` owns dataset/evaluation evidence schema for request, snapshot, split, label, run, and promotion metric rows.
- `model_governance/promotion/` owns model config, candidate, decision, activation, rollback, persistence SQL rendering, and agent-backed promotion review surfaces. Accepted promotion activation is recorded in `model_promotion_activation` and reflected in `model_config_version`; deferred or rejected decisions leave active status unchanged.

Runtime scripts may import this code; `src/` must not import `scripts/`.
