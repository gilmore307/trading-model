# Architecture

Status: accepted six-model topology
Owner intent: reduce serial model-error propagation while keeping target selection, event reasoning, decision, option expression, and residual event governance explicit.

## Module Map

| Docs band | Implementation surface | Purpose |
|---|---|---|
| `10_*` through `15_*` | `src/models/model_01_background_context/` through `src/models/model_06_residual_event_governance/`; matching `scripts/models/model_*/` | Current six model contracts and local builders. |
| `20_*` | shared model-contract/taxonomy helpers | Model decomposition, vector taxonomy, state-vector feature registry, and framework-readiness policy. |
| `30_*` | `src/model_governance/promotion/`, `scripts/model_governance/` | Promotion readiness and acceptance evidence. |
| `40_*` | historical/realtime handoff docs and governance code | Dataset scope and realtime decision handoff boundaries. |
| `50_*` | event-family research helpers | Event-family scouting, packets, and final event-layer judgment. |

Retired ten-layer packages under `src/models/model_01_market_regime/` through `src/models/model_10_event_risk_governor/` may remain as migration-source implementation surfaces only. They are not current model contracts.

## Architecture Summary

```text
point-in-time data foundation
  -> M01 Background Context
  -> M02 Target State / Selection
  -> M03 Event State / Event Conditioning
  -> M04 Unified Decision
  -> optional M05 Option Expression
  -> M06 Residual Event Governance
  -> unified decision record / downstream execution handoff
```

| Model | Stable id | Stable surface | Conceptual output | Role |
|---|---|---|---|---|
| `M01` Background Context | `background_context_model` | `model_01_background_context` | `background_context_state` | Broad market plus sector/industry background state. |
| `M02` Target State | `target_state_model` | `model_02_target_state` | `target_context_state` | Target eligibility, ranking, and anonymous target-state evidence. |
| `M03` Event State | `event_state_model` | `model_03_event_state` | `event_state_vector` | Accepted event-family/window exposure, uncertainty, relevance, and event-conditioned response/risk. |
| `M04` Unified Decision | `unified_decision_model` | `model_04_unified_decision` | `unified_decision_vector` | Direct-underlying decision with structured edge, risk, exposure, and action heads. |
| `M05` Option Expression | `option_expression_model` | `model_05_option_expression` | `trading_guidance_record`, `option_expression_plan`, `expression_vector` | Optional option/underlying expression from clean direct-underlying intent and option-chain context. |
| `M06` Residual Event Governance | `residual_event_governance_model` | `model_06_residual_event_governance` | `event_risk_intervention` / future event-family packet eligibility | Missed-event checks, residual intervention, attribution, and event-family promotion evidence. |

## Separation Rules

- M01 does not choose targets, actions, options, or event-family parameters.
- M02 is the first target-aware model and must keep raw ticker/company identity out of fitted vectors.
- M03 consumes accepted event contracts as frozen event parameters; it estimates event response/risk but does not mutate event-family identity, scope, visibility, or impact windows.
- M04 owns the direct-underlying decision and must keep structured heads for edge, risk, exposure, and action rather than collapsing the decision into one opaque score.
- M05 remains separate because option-chain, liquidity, volatility, theta, spread, DTE, and structure constraints are a distinct expression domain.
- M06 remains separate and auditable; it is residual event governance, not a hidden alpha/action model.
- Broker mutation and live/paper order placement are outside `trading-model`.

## Model Artifact Rule

Implemented model contracts separate the primary output from review and gating surfaces:

```text
model_NN_<model_slug>
model_NN_<model_slug>_explainability
model_NN_<model_slug>_diagnostics
```

The primary output is the narrow downstream dependency contract. Explainability owns human-review internals. Diagnostics owns acceptance, monitoring, and gating evidence. Model-owned fields use compact model prefixes consistently across docs, model-facing payloads, and SQL physical columns.

`docs/21_vector_taxonomy.md` owns the cross-model vocabulary for feature surfaces, feature vectors, states, state vectors, scores, diagnostics, explainability, labels, and outcomes.

`docs/23_model_learning_design.md` owns the long-term learning route for each model contract. It separates conditional estimators, policy/utility optimizers, deterministic hard constraints, and post-hoc attribution so implementation work does not turn one score into prediction, sizing, action, and explanation at once.

## Historical Sampling vs Live Routing

Historical training may use a broader point-in-time sampling universe than live inference routing. Live routing can be narrow because upstream models gate or prioritize candidates; historical training should not copy those gates when doing so would remove useful contrast.

The canonical policy lives in `docs/40_historical_dataset_scope.md`.

Promotion evidence should distinguish broad historical generalization from live-route simulation whenever a model trains on a broader universe than it receives in live routing.

## Component Execution Boundary

Live and replay execution route execution runtime components, not retired model layers and not model contracts pretending to be components. The component execution order is owned by `trading-execution`:

```text
component_01_intake
  -> component_02_entry or component_03_lifecycle
  -> optional component_04_expression_review
  -> component_05_order_intent
  -> component_06_execution_gate
  -> optional component_07_failure_review
```

`docs/41_realtime_decision_handoff.md` owns the model-side route-plan contract for those execution components. Training/evaluation may preserve full-minute state coverage, while live/replay C-component invocation may be conditional for latency, cost, account sleeve, open-position state, and option applicability.

## Point-in-Time Rule

At prediction time `t`, every model may use only data genuinely available before or at `t`.

Timestamp roles:

| Field | Meaning |
|---|---|
| `event_time` | When the underlying event occurred or became scheduled. |
| `available_time` | When the evidence/model output became visible for use. |
| `tradeable_time` | Earliest realistic time the strategy could act on the evidence. |

Backtests must use `available_time` and `tradeable_time`, not hindsight event interpretation.

## Repository Boundary

| Responsibility | Owner |
|---|---|
| Source acquisition and source evidence | `trading-data` |
| Shared registry, global terms, templates, helper policy, control-plane contracts | `trading-manager` |
| Offline model research, model-local validation, model outputs, promotion evidence | `trading-model` |
| Durable storage layout, retention, backup/restore | `trading-storage` |
| Broker/account mutation and live/paper order placement | execution-side repositories |
| Presentation | `trading-dashboard` |

`trading-model` may propose shared contracts, but `trading-manager` owns the registry authority.
