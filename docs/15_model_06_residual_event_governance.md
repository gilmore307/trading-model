# Model 06 Residual Event Governance

Status: accepted current model contract; deterministic pilot present; production evidence deferred.

## Role

`M06 Residual Event Governance` owns missed-event checks, residual event-risk intervention, attribution, future event-family promotion evidence, and durable event impact-channel taxonomy. It is an auditable governance model, not a hidden alpha or action head.

## Output

```text
model_06_residual_event_governance
  -> event_risk_intervention
  -> event_risk_intervention_ref
  -> 6_* residual event score and intervention fields
  -> future event-family packet eligibility
```

The model may warn, cap, block entry, reduce/flatten review, or request human review according to accepted intervention policy. It must not mutate broker/account state or same-fold upstream features.

## Event Impact Taxonomy

M06 is the canonical home for durable event attributes, including cases where an event affects option prices more than the underlying price. Examples include:

- `triple_witching_calendar`
- `monthly_option_expiration`
- `earnings_iv_crush`
- `index_rebalance_expiry_flow`
- `volatility_surface_dislocation`

The accepted impact channels are:

- `underlying_price`
- `option_price`
- `volatility_surface`
- `option_liquidity_spread`
- `expiry_gamma_flow`

M06 owns the taxonomy, promotion criteria, and failure/residual evidence for these attributes. M03 applies the accepted attributes into point-in-time `event_state_vector` rows. M04 and M05 consume that state. M05 may price the option-expression consequence of a volatility-surface or expiry-flow state, but it must not create its own raw event ontology.

Option-sensitive does not mean option-only. A scheduled expiry-flow event may have both underlying-price and option-surface channels through hedging, liquidity, dealer positioning, and spread behavior. M06 must preserve multi-channel intensity and confidence instead of forcing a single binary label.

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
