# Contracts

Status: accepted six-model architecture
Date: 2026-06-10

## Acceptance Scope

`trading-model` has accepted contracts for the current six-model offline stack.

| Model | Stable id | Output(s) | Acceptance state |
|---|---|---|---|
| `M01` Background Context | `background_context_model` | `background_context_state` | current contract accepted; implementation migration remains evidence-gated |
| `M02` Target State | `target_state_model` | `target_context_state` | current contract accepted; implementation migration remains evidence-gated |
| `M03` Event State | `event_state_model` | `event_state_vector` | current contract accepted; implementation migration remains evidence-gated |
| `M04` Unified Decision | `unified_decision_model` | `unified_decision_vector` with structured edge/risk/exposure/action heads | deterministic pilot present; promotion evidence deferred |
| `M05` Option Expression | `option_expression_model` | optional `trading_guidance_record` plus optional `option_expression_plan` / `expression_vector` | current contract accepted; implementation migration remains evidence-gated |
| `M06` Residual Event Governance | `residual_event_governance_model` | `event_risk_intervention` / event-adjusted risk guidance / future event-family packet eligibility | current contract accepted; implementation migration remains evidence-gated |

This closes the model-design re-scope to six model contracts. It does not approve production promotion and does not claim that every retired ten-layer implementation surface has already been migrated.

Retired packages and scripts named `model_01_market_regime` through `model_10_event_risk_governor` are no longer current model contracts. They may be used only as migration-source implementation surfaces until their behavior is moved into the six accepted contracts.

## Event-Governance Acceptance

For residual event governance specifically, architecture acceptance is not production evidence completion. An event family may enter current event-state/governance workflows only after the normal event-family workflow is satisfied for its accepted use: event-family packet, canonical parser/source routing, matched controls, impact-window backtest, fold evidence, and leakage/upstream-overlap review.

`docs/23_model_learning_design.md` owns the closed-loop evidence lifecycle for the accepted six-model stack. The loop is closed through three separated paths: point-in-time inference, post-fold evaluation labels/utilities, and review-gated promotion feedback into later-fold artifacts. It does not create a live recursive learning loop, same-fold upstream mutation, production activation, broker/account mutation, or a new model layer.

## Boundary Acceptance

After M06, work crosses into downstream review / execution-owned boundaries. Broker order construction, routing, time-in-force, send/cancel/replace, fills, broker order ids, account mutation, live scheduling, lifecycle retries, and paper/live order placement remain outside this repository.

M04 produces the base direct-underlying action thesis. M05 may compose optional offline trading guidance and option-expression context from that thesis. M06 may intervene for high-severity residual event risk by blocking new entries, capping exposure, reducing exposure, or nominating flatten/halt/human-review actions. M06 must not directly send broker orders or mutate accounts; execution risk-control owns any resulting broker action.

## Historical-Training Readiness Classification

There are no active model-stack boundary work items for the no-broker historical-training preparation boundary. The next work is objective-contract completion and run/evidence production during formal historical-training passes:

- build point-in-time inference/evaluation datasets from accepted historical source routes;
- use `docs/30_promotion_readiness.md` as the required evidence checklist and status matrix;
- calibrate labels and thresholds on chronological splits;
- prove baseline improvement, stability, leakage safety, and calibration quality;
- persist promotion evidence and accepted review decisions through the manager/storage paths;
- keep shared names and durable contracts routed through `trading-manager/scripts/registry/`.

Execution-facing unified decision-record artifacts remain outside the current no-broker historical-training scope unless explicitly accepted later.

`trading-model` should be treated as structurally closed for the accepted six-model architecture boundary. Future changes should be scoped as objective-contract implementation, production hardening, evidence/promotion work, bug fixes, or explicitly accepted contract changes.
