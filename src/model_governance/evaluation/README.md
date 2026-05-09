# evaluation

Dataset and evaluation evidence governance for `trading-model`.

This package owns schema helpers for reproducible evaluation evidence:

- `model_dataset_request`
- `model_dataset_snapshot`
- `model_dataset_split`
- `model_eval_label`
- `model_eval_run`
- `model_promotion_metric`

It does not own model activation, rollback, durable promotion decisions, or production pointers. Those lifecycle concerns belong in `trading-manager`; model-side reviewer artifacts live in `model_governance/promotion/`.
