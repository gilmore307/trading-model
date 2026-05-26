# evaluation

Dataset and evaluation evidence governance for `trading-model`.

This package owns schema helpers for reproducible evaluation evidence:

- `model_dataset_request`
- `model_dataset_snapshot`
- `model_dataset_split`
- `model_eval_label`
- `model_eval_run`
- `model_promotion_metric`

It does not own runtime activation, active-pointer writes, broker routes, or production trading pointers. Evaluation-owned promotion readiness lives in `trading-evaluation`; runtime lifecycle and active-pointer writes belong in `trading-execution`; model-side reviewer artifacts live in `model_governance/promotion/`.
