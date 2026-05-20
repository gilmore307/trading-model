# Contracts

Status: accepted model-design acceptance for Layers 1-10 architecture; DynamicRiskPolicyModel physical implementation pending
Date: 2026-05-07

## Acceptance scope

`trading-model` has a complete accepted local deterministic scaffold for the current offline model stack:

| Layer | Model | Output | Acceptance state |
|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_context_state` | accepted V2.2 contract, deterministic implementation/evaluation path, production promotion still evidence-gated |
| 2 | `SectorContextModel` | `sector_context_state` | accepted direction-neutral contract, deterministic implementation/evaluation path, production promotion still evidence-gated |
| 3 | `TargetStateVectorModel` | `target_context_state` | accepted direction-neutral target-state contract, anonymous candidate preprocessing, deterministic implementation/evaluation scaffold |
| 4 | `EventFailureRiskModel` | `event_failure_risk_vector` | accepted pre-implementation contract; physical implementation pending dedicated slice |
| 5 | `AlphaConfidenceModel` | `alpha_confidence_vector` | accepted base-alpha V1 scaffold; physical surface `model_05_alpha_confidence` |
| 6 | `DynamicRiskPolicyModel` | `dynamic_risk_policy_state` | accepted architecture boundary; physical implementation pending dedicated slice |
| 7 | `PositionProjectionModel` | `position_projection_vector` | accepted V1 scaffold; physical surface `model_07_position_projection` |
| 8 | `UnderlyingActionModel` | `underlying_action_plan` / `underlying_action_vector` | accepted offline direct-underlying action scaffold; physical surface `model_08_underlying_action` |
| 9 | `TradingGuidanceModel / OptionExpressionModel` | optional `trading_guidance_record` plus optional `option_expression_plan` / `expression_vector` | accepted optional offline trading-guidance boundary; V1 option-expression subset currently uses physical surface `model_09_option_expression` |
| 10 | `EventRiskGovernor / EventIntelligenceOverlay` | `event_risk_intervention` / event-adjusted risk guidance | accepted event-risk governor boundary over the Layer 8 direct-underlying thesis; physical surface `model_10_event_risk_governor` |

This closes the model-design phase. It does not approve production promotion.

## Boundary acceptance

Layer 9 is now TradingGuidance / OptionExpression / optional expression context and Layer 10 is EventRiskGovernor / EventIntelligenceOverlay / realtime risk handoff. There is no accepted Layer 11 inside `trading-model`.

After Layer 10, work crosses into downstream review / execution-owned boundaries. Broker order construction, routing, time-in-force, send/cancel/replace, fills, broker order ids, account mutation, live scheduling, lifecycle retries, and paper/live order placement remain outside this repository.

Layer 8 produces the base direct-underlying action thesis. Layer 10's canonical intervention target is that Layer 8 underlying/spot thesis; it may intervene for high-severity residual event risk by blocking new entries, capping exposure, reducing exposure, or nominating flatten/halt/human-review actions. Layer 9 may compose optional offline trading guidance and option-expression context from the Layer 8 thesis. Layer 10 event-risk governance uses the Layer 8 thesis as the canonical intervention target and may attach Layer 9 context when available. For crypto/direct-underlying-only routes, option-expression evidence is not required. Layer 10 still must not directly send broker orders or mutate accounts; execution risk-control owns any resulting broker action.

## Historical-training readiness classification

There are no active model-stack design work items for the current no-broker historical-training preparation boundary. The next work is run/evidence production during formal historical-training passes:

- build point-in-time inference/evaluation datasets from accepted historical source routes;
- use `docs/30_promotion_readiness.md` as the required evidence checklist and status matrix;
- calibrate labels and thresholds on chronological splits;
- prove baseline improvement, stability, leakage safety, and calibration quality;
- persist promotion evidence and accepted review decisions through the manager/storage paths;
- keep shared names and durable contracts routed through `trading-manager/scripts/registry/`.

Execution-facing unified decision-record artifacts remain outside the current no-broker historical-training scope unless explicitly accepted later.

## Verification receipt

Latest acceptance verification for this acceptance:

```text
trading-model: PYTHONPATH=src python3 -m unittest discover tests -> 94 tests OK
trading-manager: PYTHONPATH=src python3 -m unittest discover tests -> 35 tests OK
trading-manager: python3 scripts/registry/apply_registry_migrations.py --dry-run -> no pending migrations
git diff --check clean in both repositories
```

Latest relevant pushed commits before the final acceptance-doc commit:

```text
trading-model  34f8cd0 Tighten layer eight candidate filters
trading-manager 633c2cb Register layer eight candidate filter policy
```

After this acceptance document lands, `trading-model` should be treated as structurally closed for the accepted Layers 1-9 architecture phase. Future changes should be scoped as production hardening, evidence/promotion work, bug fixes, or explicitly accepted architecture revisions.
