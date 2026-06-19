# Model Decomposition Framework

Status: accepted six-model decomposition spine; production promotion remains evidence-gated
Owner intent: every current model contract must keep the same reviewable decomposition before implementation or promotion expands.

## Nine-Part Structure

For each current model contract, define:

1. **Data** — eligible point-in-time input tables/artifacts, owner, and availability timestamp.
2. **Features** — model-facing `X`, diagnostic fields, evaluation-only fields, and intentionally unused fields.
3. **Prediction target / utility** — supervised target, rank objective, inferred latent state, or utility surface.
4. **Model mapping** — how `X` becomes the output state/vector/ranker/gate.
5. **Loss / error measure** — how wrongness is measured during fitting, scoring, calibration, or evaluation.
6. **Training / parameter update** — how scalers, thresholds, rules, or learned parameters update without leakage.
7. **Validation / usefulness** — how the model proves decision usefulness, not just historical fit.
8. **Overfitting control** — how the model avoids hindsight, data snooping, unstable refits, and false confidence.
9. **Decision deployment** — how the output enters the offline decision record and downstream gates.

## Current Model Contracts

```text
M01 Background Context          -> background_context_state
M02 Target State / Selection    -> target_context_state
M03 Event State / Conditioning  -> event_state_vector
M04 Unified Decision            -> unified_decision_vector
M05 Option Expression           -> option_expression_plan / expression_vector
M06 Residual Event Governance   -> event_risk_intervention / future event-family packet eligibility
```

## Cross-Model Rules

### Model Artifact Split

Each implemented current model contract should separate three artifact classes:

```text
model_NN_<model_slug>                  # primary output
model_NN_<model_slug>_explainability   # human review/debug/explain
model_NN_<model_slug>_diagnostics      # acceptance/monitoring/gating
```

Primary outputs stay narrow and stable. Explainability and diagnostics may be wider, but downstream production logic should not hard-depend on them without a reviewed promotion decision.

Local generator scripts may emit nested JSON/JSONL fixture rows for smoke evidence. Persisted SQL artifact closure should use the primary/support split above: primary rows own stable refs and resolved scalar fields; `_explainability` and `_diagnostics` own nested payloads, review detail, and monitoring evidence.

- Every row must be point-in-time and keyed by a timestamp genuinely knowable to the system.
- Data acquisition/source evidence stays in `trading-data`.
- Global terms, fields, artifacts, statuses, templates, and contracts route through `trading-manager`.
- Do not collapse rich context into a scalar unless supporting fields remain available for audit and downstream interpretation.
- Use `docs/21_vector_taxonomy.md` as the vocabulary authority: feature surfaces feed models, feature vectors are model-facing inputs, states/state vectors are model outputs, scores are scalar dimensions, labels/outcomes are training/evaluation-only.
- Live/paper order mutation remains outside `trading-model`.
- Historical retired serial package, script, and table names should not define new current contracts.

## Model Roles

| Model | Role | Core validation question |
|---|---|---|
| `M01` Background Context | Conditional background estimator | Does market/sector/industry context improve downstream target/decision calibration without selecting targets directly? |
| `M02` Target State | Target-state estimator/ranker | Does the target-state output improve target selection and downstream decision quality without identity leakage? |
| `M03` Event State | Event-conditioned response/risk estimator | Does accepted event-state evidence improve failure-risk and path-risk handling without becoming standalone event alpha? |
| `M04` Unified Decision | Direct-underlying policy/utility optimizer | Does one decision model improve after-cost utility, drawdown/CVaR, turnover, no-trade calibration, action stability, and explainability versus the retired serial route? |
| `M05` Option Expression | Option/expression utility optimizer | Does option-expression selection improve realistic after-cost expression utility without best-contract hindsight or broker leakage? |
| `M06` Residual Event Governance | Residual governance and attribution model | Does residual event intervention reduce tail failures and attribution misses without excessive overblocking or same-fold upstream mutation? |

## Learning Role

The long-term learning role for each current model contract is defined in `docs/23_model_learning_design.md`. This file owns the nine-part decomposition contract; it should not preserve retired scaffold phases as model objectives.
