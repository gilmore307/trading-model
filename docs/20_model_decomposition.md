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

### Probabilistic Factor Ownership

M01-M03 publish independent point-in-time probabilistic factors in a shared
review language. They are not three unrelated probability spaces, and they must
not progressively mutate one hidden decision curve. M04 is the only current
owner of calibrated fusion, interaction, final trade posterior, and action
thresholding.

```text
M01 Background Context -> market/background prior and uncertainty
M02 Target State       -> target residual likelihood / target base curve
M03 Event State        -> event residual log-odds delta, gate, and uncertainty
M04 Unified Decision   -> calibrated fusion and final tradable decision surface
M05 Option Expression  -> expression/payoff/instrument translation
```

M02 and M03 may consume upstream state only as fixed point-in-time context,
applicability metadata, or conditional keys. They must not re-model or
re-count the upstream probability contribution as their own evidence. M04 owns
cross-factor interaction and composition. If post-replay review finds M01, M02,
and M03 independently acceptable but final selected performance is poor, the
first model-layer attribution should move to M04 fusion, weighting, calibration,
or thresholding unless an interface/handoff defect is shown earlier.

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

## Post-Replay Review Responsibility

Each M01-M03 row must have its own review path and outcome-label join before
the pipeline can claim the upstream factor was correct:

- M01 review joins background states to replay-time market/context outcome
  labels.
- M02 review joins every visible same-timestamp candidate row to candidate
  forward-return/rank labels, not only the selected target.
- M03 review joins each point-in-time event-pool row to event-window outcome,
  overblock, underblock, and path-deviation labels.

Missing M01-M03 labels are review evidence gaps, not evidence that M04 is at
fault. Once M01-M03 factor rows are independently acceptable, M04 owns poor
final decision performance unless the evidence shows an explicit interface or
handoff defect.

M05 is reviewed after M04 against point-in-time option-expression candidates,
realistic cost/fill/theta/IV outcomes, and direction consistency. M05 may expose
an expression failure, but it must not relitigate the target-level M04 thesis.

## Learning Role

The long-term learning role for each current model contract is defined in `docs/23_model_learning_design.md`. This file owns the nine-part decomposition contract; it should not preserve retired scaffold phases as model objectives.
