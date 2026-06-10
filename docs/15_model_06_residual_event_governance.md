# Model 06 Residual Event Governance

Status: accepted current model contract; deterministic pilot present; production evidence deferred.

## Role

`M06 Residual Event Governance` owns missed-event checks, residual event-risk intervention, attribution, and future event-family promotion evidence. It is an auditable governance model, not a hidden alpha or action head.

## Output

```text
model_06_residual_event_governance
  -> event_risk_intervention
  -> event_risk_intervention_ref
  -> 6_* residual event score and intervention fields
  -> future event-family packet eligibility
```

The model may warn, cap, block entry, reduce/flatten review, or request human review according to accepted intervention policy. It must not mutate broker/account state or same-fold upstream features.

## Inputs

- `background_context_state`.
- `target_context_state`.
- `event_state_vector`.
- `unified_decision_vector` / `unified_decision_vector_ref`.
- Optional `option_expression_plan` / `option_expression_plan_ref`.
- Point-in-time event observations, source/revision provenance, scope mapping, residual anomaly evidence, and overblock/accounting diagnostics.

## Current Implementation

`src/models/model_06_residual_event_governance/` contains a deterministic pilot.
It consumes current M04/M05 thesis references, transforms retained event-risk
scoring into current `6_*` fields, emits `event_risk_intervention`, and keeps
future labels in the offline evaluation helper only.

Current local entrypoints:

```text
scripts/models/model_06_residual_event_governance/generate_model_06_residual_event_governance.py
scripts/models/model_06_residual_event_governance/evaluate_model_06_residual_event_governance.py
scripts/models/model_06_residual_event_governance/review_residual_event_governance_promotion.py
```

The pilot is not production promotion evidence. Real promotion still requires
point-in-time residual-event labels, baseline comparison, overblock/accounting
metrics, leakage checks, stability, calibration, and manager-side review.

## Migration Source

Retired implementation package `model_10_event_risk_governor` may be used as source material during migration. It is not a separate current model contract.
