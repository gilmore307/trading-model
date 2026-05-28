# Contracts

Status: accepted model-design acceptance for Layers 1-10 architecture
Date: 2026-05-07

## Acceptance scope

`trading-model` has accepted contracts for the current offline model stack. `docs/23_model_learning_design.md` owns the learning role for each layer: conditional estimator, policy/utility optimizer, deterministic hard constraint, or post-hoc attribution.

| Layer | Model | Output | Acceptance state |
|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_context_state` | conditional market-state estimator; production promotion remains evidence-gated |
| 2 | `SectorContextModel` | `context_etf_state` | conditional ETF-context estimator; production promotion remains evidence-gated |
| 3 | `TargetStateVectorModel` | `target_context_state` | anonymous target-state estimator plus candidate preprocessing; production promotion remains evidence-gated |
| 4 | `EventFailureRiskModel` | `event_failure_risk_vector` | reviewed event-failure-risk estimator; production promotion remains evidence-gated |
| 5 | `AlphaConfidenceModel` | `alpha_confidence_vector` | calibrated after-cost edge estimator; production promotion remains evidence-gated |
| 6 | `DynamicRiskPolicyModel` | `dynamic_risk_policy_state` | portfolio risk-policy optimizer; production promotion remains evidence-gated |
| 7 | `PositionProjectionModel` | `position_projection_vector` | exposure utility optimizer; production promotion remains evidence-gated |
| 8 | `UnderlyingActionModel` | `underlying_action_plan` / `underlying_action_vector` | structured underlying-action policy; production promotion remains evidence-gated |
| 9 | `TradingGuidanceModel / OptionExpressionModel` | optional `trading_guidance_record` plus optional `option_expression_plan` / `expression_vector` | expression utility optimizer and offline guidance boundary; production promotion remains evidence-gated |
| 10 | `EventRiskGovernor / EventIntelligenceOverlay` | `event_risk_intervention` / event-adjusted risk guidance | residual event-risk intervention and attribution boundary; production promotion remains evidence-gated |

This closes the model-design phase. It does not approve production promotion.

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

`trading-model` should be treated as structurally closed for the accepted Layers 1-10 architecture boundary. Future changes should be scoped as objective-contract implementation, production hardening, evidence/promotion work, bug fixes, or explicitly accepted contract changes.
