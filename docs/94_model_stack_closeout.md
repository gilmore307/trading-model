# Model Stack Closeout

Status: accepted model-design closeout for Layers 1-8
Date: 2026-05-07

## Closeout scope

`trading-model` has a complete accepted local deterministic scaffold for the current offline model stack:

| Layer | Model | Output | Closeout state |
|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_context_state` | accepted V2.2 contract, deterministic implementation/evaluation path, production promotion still evidence-gated |
| 2 | `SectorContextModel` | `sector_context_state` | accepted direction-neutral contract, deterministic implementation/evaluation path, production promotion still evidence-gated |
| 3 | `TargetStateVectorModel` | `target_context_state` | accepted direction-neutral target-state contract, anonymous candidate preprocessing, deterministic implementation/evaluation scaffold |
| 4 | `AlphaConfidenceModel` | `alpha_confidence_vector` | accepted base-alpha V1 scaffold; current surface `model_04_alpha_confidence` |
| 5 | `PositionProjectionModel` | `position_projection_vector` | accepted V1 scaffold; current surface `model_05_position_projection` |
| 6 | `UnderlyingActionModel` | `underlying_action_plan` / `underlying_action_vector` | accepted offline direct-underlying action scaffold; current surface `model_06_underlying_action` |
| 7 | `TradingGuidanceModel / OptionExpressionModel` | `trading_guidance_record` plus optional `option_expression_plan` / `expression_vector` | accepted base trading-guidance boundary; V1 option-expression subset uses current surface `model_07_option_expression` |
| 8 | `EventRiskGovernor / EventIntelligenceOverlay` | `event_risk_intervention` / event-adjusted risk guidance | accepted event-risk governor boundary; legacy event-overlay physical surface `model_08_event_risk_governor` until migration |

This closes the model-design phase. It does not approve production promotion.

## Boundary closeout

There is no accepted Layer 9 inside `trading-model`.

After Layer 8, work crosses into downstream review / execution-owned boundaries. Broker order construction, routing, time-in-force, send/cancel/replace, fills, broker order ids, account mutation, live scheduling, lifecycle retries, and paper/live order placement remain outside this repository.

Layer 7 produces the base offline trading-guidance candidate. Layer 8 may intervene on that candidate for high-severity event risk by blocking new entries, capping exposure, reducing exposure, or nominating flatten/halt/human-review actions. Layer 8 still must not directly send broker orders or mutate accounts; execution risk-control owns any resulting broker action.

## Historical-training readiness classification

There are no active model-stack design work items for the current no-broker historical-training preparation boundary. The next work is run/evidence production during formal historical-training passes:

- build point-in-time inference/evaluation datasets from accepted historical source routes;
- use `docs/95_promotion_readiness.md` as the required evidence checklist and status matrix;
- calibrate labels and thresholds on chronological splits;
- prove baseline improvement, stability, leakage safety, and calibration quality;
- persist promotion evidence and accepted review decisions through the manager/storage paths;
- keep shared names and durable contracts routed through `trading-manager/scripts/registry/`.

Execution-facing unified decision-record artifacts remain outside the current no-broker historical-training scope unless explicitly accepted later.

## Verification receipt

Latest closeout verification for this closeout:

```text
trading-model: PYTHONPATH=src python3 -m unittest discover tests -> 94 tests OK
trading-manager: PYTHONPATH=src python3 -m unittest discover tests -> 35 tests OK
trading-manager: python3 scripts/registry/apply_registry_migrations.py --dry-run -> no pending migrations
git diff --check clean in both repositories
```

Latest relevant pushed commits before the final closeout-doc commit:

```text
trading-model  34f8cd0 Tighten layer eight candidate filters
trading-manager 633c2cb Register layer eight candidate filter policy
```

After this closeout document lands, `trading-model` should be treated as structurally closed for the accepted Layers 1-8 model-design phase. Future changes should be scoped as production hardening, evidence/promotion work, bug fixes, or explicitly accepted architecture revisions.
