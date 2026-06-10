# Contracts

Status: accepted six-training-block topology preserving Layers 1-10 runtime contracts
Date: 2026-06-10

## Acceptance scope

`trading-model` has accepted contracts for the current offline model stack. The repository now distinguishes training topology from runtime contracts:

- training topology: six model blocks (`M01-M02`, `M03`, `M04`, `M05-M08`, `M09`, `M10`);
- runtime contracts: the ten explicit `M01` through `M10` outputs that live/paper components consume, route, audit, or govern.

`docs/23_model_learning_design.md` owns the learning role for each block/contract: conditional estimator, policy/utility optimizer, deterministic hard constraint, or post-hoc attribution.

| Training block | Runtime contract(s) | Output(s) | Acceptance state |
|---|---|---|---|
| `B01` Background Context | `M01` Market Regime + `M02` Sector Context | `market_context_state`, `context_etf_state` | shared background training block accepted; production promotion remains evidence-gated |
| `B02` Target State / Selection | `M03` Target State | `target_context_state` | target selection/state contract remains explicit; production promotion remains evidence-gated |
| `B03` Event State / Conditioning | `M04` Event Failure Risk | `event_failure_risk_vector` | event reasoning contract remains explicit; production promotion remains evidence-gated |
| `B04` Unified Decision | `M05` Alpha Confidence + `M06` Dynamic Risk Policy + `M07` Position Projection + `M08` Underlying Action | `alpha_confidence_vector`, `dynamic_risk_policy_state`, `position_projection_vector`, `underlying_action_plan` / `underlying_action_vector` | unified internal decision training block accepted as target topology; runtime fields remain structured; production promotion remains evidence-gated |
| `B05` Option Expression | `M09` Trading Guidance / Option Expression | optional `trading_guidance_record` plus optional `option_expression_plan` / `expression_vector` | separate option-expression domain remains explicit; production promotion remains evidence-gated |
| `B06` Residual Event Governance | `M10` Event Risk Governor / Event Intelligence Overlay | `event_risk_intervention` / event-adjusted risk guidance | residual event governance remains separate and auditable; production promotion remains evidence-gated |

This closes the model-design re-scope for training topology. It does not approve production promotion and does not delete current `model_01_*` through `model_10_*` implementation surfaces.

For Layer 10 specifically, model-design acceptance is not evidence completion. Layer 10 evidence is complete only after the active event-family universe has passed the normal event-family workflow: event-family packets, canonical parser/source routing, matched controls, impact-window backtests, fold stability, and leakage/upstream-overlap review. Closed-loop replay overlays and a few calibrated seed families are evidence progress, not completion.

`docs/23_model_learning_design.md` owns the closed-loop evidence lifecycle for the accepted six-block / ten-contract stack. The loop is closed through three separated paths: point-in-time inference, post-fold evaluation labels/utilities, and review-gated promotion feedback into later-fold artifacts. It does not create a live recursive learning loop, same-fold upstream mutation, production activation, broker/account mutation, or a new model layer.

## Boundary acceptance

Layer 9 is TradingGuidance / OptionExpression / optional expression context and Layer 10 is EventRiskGovernor / EventIntelligenceOverlay / realtime risk handoff. There is no accepted Layer 11 inside `trading-model`.

After Layer 10, work crosses into downstream review / execution-owned boundaries. Broker order construction, routing, time-in-force, send/cancel/replace, fills, broker order ids, account mutation, live scheduling, lifecycle retries, and paper/live order placement remain outside this repository.

Layer 8 produces the base direct-underlying action thesis. Layer 10's canonical intervention target is that Layer 8 underlying/spot thesis; it may intervene for high-severity residual event risk by blocking new entries, capping exposure, reducing exposure, or nominating flatten/halt/human-review actions. Layer 9 may compose optional offline trading guidance and option-expression context from the Layer 8 thesis. Layer 10 event-risk governance uses the Layer 8 thesis as the canonical intervention target and may attach Layer 9 context when available. For crypto/direct-underlying-only routes, option-expression evidence is not required. Layer 10 still must not directly send broker orders or mutate accounts; execution risk-control owns any resulting broker action.

## Historical-training readiness classification

There are no active model-stack boundary work items for the no-broker historical-training preparation boundary. The next work is objective-contract completion and run/evidence production during formal historical-training passes:

- build point-in-time inference/evaluation datasets from accepted historical source routes;
- use `docs/30_promotion_readiness.md` as the required evidence checklist and status matrix;
- calibrate labels and thresholds on chronological splits;
- prove baseline improvement, stability, leakage safety, and calibration quality;
- persist promotion evidence and accepted review decisions through the manager/storage paths;
- keep shared names and durable contracts routed through `trading-manager/scripts/registry/`.

Execution-facing unified decision-record artifacts remain outside the current no-broker historical-training scope unless explicitly accepted later.

`trading-model` should be treated as structurally closed for the accepted six-training-block / ten-runtime-contract architecture boundary. Future changes should be scoped as objective-contract implementation, production hardening, evidence/promotion work, bug fixes, or explicitly accepted contract changes.
