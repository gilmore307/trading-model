# Decisions

This file records the current accepted decisions for `trading-model`. Historical route changes remain in Git history; this file describes the live architecture directly.

## D001 - Repository boundary

Date: 2026-04-25
Status: Accepted

`trading-model` owns offline modeling research, validation, model-local outputs, promotion evidence, and decision-record prototypes for the trading decision stack.

It does not own raw source acquisition, global registry authority, durable storage policy, scheduling/lifecycle routing, live/paper order placement, broker/account mutation, dashboards, secrets, or committed generated runtime artifacts.

Cross-repository names, shared fields, artifact types, statuses, templates, and contracts must be routed through `trading-manager` before other repositories depend on them.

## D002 - Direction-neutral model stack

Date: 2026-04-27
Status: Accepted

`trading-model` is the offline modeling home for the current six-model decision stack:

| Model | Stable id | Role |
|---|---|---|
| `M01 Background Context` | `background_context_model` | Broad market plus sector/industry context state. |
| `M02 Target State` | `target_state_model` | Target selection, ranking, and anonymous target-state evidence. |
| `M03 Event State` | `event_state_model` | Accepted event-family/window/exposure/uncertainty conditioning. |
| `M04 Unified Decision` | `unified_decision_model` | Direct-underlying edge, risk, exposure, no-trade, and action thesis with structured heads. |
| `M05 Option Expression` | `option_expression_model` | Optional option/underlying expression from M04 `direct_underlying_intent` and point-in-time option-chain context. |
| `M06 Residual Event Governance` | `residual_event_governance_model` | Residual event-risk intervention, missed-event attribution, and future event-family evidence. |

Live/paper order placement remains outside this repository and no layer should be renamed live `ExecutionModel`.

## D003 - Current structure separates market, sector, and target work

Date: 2026-05-02
Status: Accepted

The current route is:

```text
M01 BackgroundContextModel
  -> background_context_state

M02 TargetStateModel
  -> target_context_state

M03 EventStateModel
  -> event_state_vector

M04 UnifiedDecisionModel
  -> unified_decision_vector
  -> direct_underlying_intent

M05 OptionExpressionModel
  -> option_expression_plan / expression_vector

M06 ResidualEventGovernanceModel
  -> event_risk_intervention
```

Hard separation rules:

- M01 describes broad market plus sector/industry background.
- M02 is the target-state and target-selection boundary.
- M03 is the event-state boundary.
- Final target/security choice must be made downstream from accepted target-state evidence, not from raw identity.
- Model-facing fitting rows for target work must anonymize ticker/company identity.
- Real symbols may remain in audit/routing metadata and decision records, but not in model-facing identity features.

## D004 - Current six-model contracts are the only active model-contract standard

Date: 2026-06-10
Status: Accepted

The current model-contract standard is M01 through M06 only. Historical retired serial package names, old layer terminology, and serial alpha/risk/position/action handoffs are not active contracts, active entrypoints, or maintained source surfaces in the repository.

Accepted current model contracts:

- M01 `background_context_model`: broad market plus sector/industry background state.
- M02 `target_state_model`: target eligibility, ranking, and anonymous target-state evidence.
- M03 `event_state_model`: accepted event-family/window/exposure/uncertainty conditioning.
- M04 `unified_decision_model`: direct-underlying edge, risk, exposure, no-trade, allocation, and action thesis with structured heads.
- M05 `option_expression_model`: optional option/underlying expression from M04 direct intent and point-in-time option-chain context.
- M06 `residual_event_governance_model`: residual event-risk intervention, missed-event attribution, and future event-family evidence.

Any new model-facing route, doc, script, test, table, or registry proposal must use these six contracts directly.

## D005 - M04 owns allocation and forbids tactical increase actions

Date: 2026-06-19
Status: Accepted

M04 emits `4_target_allocation_fraction_<horizon>` and `4_resolved_target_allocation_fraction` as target allocation percentages of total portfolio/account budget. Replay and execution convert the resolved fraction into notional and option contract quantity; they must not invent a separate fixed notional or hidden cap.

Executable tactical add/increase actions are disabled under the current full-allocation policy. Existing same-direction positions with additional positive gap resolve to maintain, while winners naturally grow as their marked value rises. Risk-reduction actions remain valid, including reduce, close, cover, stop, and take-profit paths.

## D006 - Rebalance replaces only for invalidation or significant superiority

Date: 2026-06-19
Status: Accepted

Portfolio replay and execution distinguish two replacement cases:

- If an existing position is no longer suitable, lifecycle exits or reduces it first; released capital may then enter the normal ranked candidate path.
- If an existing position remains suitable but a new candidate is better, replacement is allowed only when the new candidate exceeds the worst held position by an explicit switch threshold after costs and feasibility checks.

Default operation has an explicit finite portfolio-capacity cap. The current equity/options default is five simultaneous risk slots, derived from the `0.20` default target-allocation fraction. Position replacement is therefore a deliberate policy action after capacity is full, not continuous optimization churn; research runs may use an explicit wider or unbounded override, but those runs are a different portfolio policy and are not promotion-compatible by default.

## D007 - Production promotion remains evidence-gated

Date: 2026-06-10
Status: Accepted

Deterministic pilots and local chain smoke tests prove structural contracts only. Production promotion still requires point-in-time training data, walk-forward replay, calibration, leakage checks, cost/fill sensitivity, option-chain evidence where applicable, baseline comparison, and manager-side promotion review. Broker orders and account mutation remain outside `trading-model`.

## D008 - Learned model schemes are selected per layer

Date: 2026-06-28
Status: Accepted

The active model-framework route is replayable cumulative learning. Each M01-M06 layer must have exactly one active learned model scheme at a time, selected for that layer's target, data shape, replay requirements, and operational constraints. Different layers may use different model families.

The rule is not "one model family for all six layers." The rule is "one active scheme per layer." Once a layer selects its active scheme, prior alternatives for that layer are retired from runtime use and no parallel challenger route is maintained for that layer. Offline research may still produce evidence for a future replacement, but replacement must retire the previous active scheme for that layer in the same acceptance batch.

All eligible schemes must be cumulative, checkpointable, replayable, target-anonymous, point-in-time safe, and rollbackable. Deterministic behavior remains valid for hard guardrails, schema validation, routing, and reference behavior, but it must not stand in for a learned model where the current contract requires estimation or policy optimization.

The current small `continual_residual_mlp` validation proves that one cumulative MLP implementation can train, checkpoint, restore, and emit bounded target-anonymous predictions. It is scheme viability evidence only. It is not a global mandate that all six layers must use that model family, and it is not promotion evidence.

The selected route follows `docs/24_model_framework_readiness.md`. Every learned checkpoint must first prove replay eligibility: checkpoint restore must reproduce predictions; weights, scalers, normalizers, feature maps, calibration state, and update state must be checkpointed; raw identity, surrogate identity dominance, future labels, same-fold downstream outcomes, and M06 hindsight feedback must be rejected. Promotion requires downstream-neutral or downstream-positive full-chain replay evidence, not only layer-local scores.
