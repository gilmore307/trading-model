# promotion

Promotion lifecycle governance for `trading-model`.

This package owns generic model promotion surfaces:

- `model_config_version`
- `model_promotion_candidate`
- `model_promotion_decision`
- `model_promotion_activation`
- `model_promotion_rollback`

`rows.py` builds deterministic row payloads. `schema.py` owns promotion lifecycle DDL. `persistence.py` renders audited SQL for persisting evidence, decisions, and activation events. `agent_review.py` constrains agent-backed promotion review prompts and responses.

Dataset requests, snapshots, splits, labels, eval runs, and promotion metrics remain in `model_governance/evaluation/`.
