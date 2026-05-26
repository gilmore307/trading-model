# promotion

Model-side promotion evidence helpers.

This package owns only local evidence/review artifact surfaces:

- deterministic model config refs for evidence payloads;
- deterministic promotion candidate evidence refs;
- strict reviewer prompt/response validation;
- review artifacts that can be handed to `trading-manager`.

It does **not** own promotion-readiness records, runtime activation records, rollback records, production pointers, or control-plane SQL. Promotion readiness belongs in `trading-evaluation`; runtime lifecycle and active-pointer writes belong in `trading-execution`; manager request scheduling belongs in `trading-manager`.

Dataset requests, snapshots, splits, labels, eval runs, and promotion metrics remain in `model_governance/evaluation/` as model-produced evidence.
