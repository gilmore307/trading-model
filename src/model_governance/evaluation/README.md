# evaluation

Dataset and evaluation evidence governance for `trading-model`.

This package owns schema helpers for reproducible evaluation evidence:

- `model_dataset_request`
- `model_dataset_snapshot`
- `model_dataset_split`
- `model_eval_label`
- `model_eval_run`
- `model_promotion_metric`

It also owns the model-local metric contract in
`layer_metric_contracts.py`. That contract defines which metric families and
tests are valid for each layer before any metric value is published. AUROC,
PR-AUC, Brier, and ECE are eligible only for explicit binary probabilistic
labels; representation, alpha-ranking, policy, path, option-expression, and
event-attribution layers use their own primary tests. Model-group ablation and
counterfactual replay stay group contribution evidence and must not be relabeled
as model-local metrics.

It does not own runtime activation, active-pointer writes, broker routes, or production trading pointers. Evaluation-owned promotion readiness lives in `trading-evaluation`; runtime lifecycle and active-pointer writes belong in `trading-execution`; model-side reviewer artifacts live in `model_governance/promotion/`.
