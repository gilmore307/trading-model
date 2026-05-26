# Realtime Decision Handoff

Status: accepted scaffold  
Date: 2026-05-11

## Purpose

Realtime execution capture can now produce `execution_model_decision_input_snapshot` envelopes. `trading-model` needs a model-side entry boundary that accepts those envelopes for fixture/shadow routing into the historical model stack without accidentally activating production inference or execution.

This document defines that boundary.

## Accepted chain

```text
trading-execution realtime capture
  -> realtime_feature_snapshot
  -> execution_model_decision_input_snapshot
  -> model_realtime_decision_route_plan
  -> fixture/shadow historical-model generation route
```

`model_realtime_decision_route_plan` is a route plan, not a model output. It validates required Layer 1-8 and Layer 10 input refs, accepts Layer 9 trading-guidance / option-expression refs when available, maps each present layer to its reviewed model generator entrypoint, and records the handoff mode. Direct-underlying routes must not require Layer 9 option refs.

Accepted handoff modes:

- `fixture_replay`
- `shadow_monitoring`

## Required input

The model-side planner consumes an `execution_model_decision_input_snapshot` object with:

- `decision_input_snapshot_id`
- `decision_time`
- `instrument_ref`
- `historical_dataset_snapshot_ref`
- `frozen_model_config_ref`
- `realtime_feature_snapshot_ref`
- exactly one required layer input for Layers 1-8 and Layer 10
- zero or one optional Layer 9 trading-guidance / option-expression input

Each conceptual layer input must include the expected model id, expected model output, feature ref, frozen model config ref, and historical dataset snapshot ref. Implementation model ids now follow the current conceptual layer numbering; this table is conceptual-order first.

## Layer route mapping

| Layer | Model id | Expected output | Route entrypoint |
|---:|---|---|---|
| 1 | `market_regime_model` | `market_context_state` | `scripts/models/model_01_market_regime/generate_model_01_market_regime.py` |
| 2 | `sector_context_model` | `sector_context_state` | `scripts/models/model_02_sector_context/generate_model_02_sector_context.py` |
| 3 | `target_state_vector_model` | `target_context_state` | `scripts/models/model_03_target_state_vector/generate_model_03_target_state_vector.py` |
| 4 | `event_failure_risk_model` | `event_failure_risk_vector` | `scripts/models/model_04_event_failure_risk/generate_model_04_event_failure_risk.py` |
| 5 | `alpha_confidence_model` | `alpha_confidence_vector` | `scripts/models/model_05_alpha_confidence/generate_model_05_alpha_confidence.py` |
| 6 | `dynamic_risk_policy_model` | `dynamic_risk_policy_state` | `scripts/models/model_06_dynamic_risk_policy/generate_model_06_dynamic_risk_policy.py` |
| 7 | `position_projection_model` | `position_projection_vector` | `scripts/models/model_07_position_projection/generate_model_07_position_projection.py` |
| 8 | `underlying_action_model` | `underlying_action_plan` | `scripts/models/model_08_underlying_action/generate_model_08_underlying_action.py` |
| 9 | `option_expression_model` | optional `trading_guidance_record` with optional `option_expression_plan` | `scripts/models/model_09_option_expression/generate_model_09_option_expression.py` |
| 10 | `event_risk_governor` | `event_context_vector` | `scripts/models/model_10_event_risk_governor/generate_model_10_event_risk_governor.py` |

## Non-authorizations

This scaffold does not:

- open provider streams;
- read secrets;
- refit models;
- activate production model configs;
- produce a promoted production decision;
- construct broker orders;
- mutate broker/account state;
- persist manager-control-plane decisions.

It only plans and validates the route from realtime input refs into the historical model stack.

## CLI

```bash
PYTHONPATH=src python3 scripts/models/plan_realtime_decision_handoff.py decision_input.json \
  --handoff-mode shadow_monitoring > route_plan.json

PYTHONPATH=src python3 scripts/models/validate_realtime_decision_handoff.py route_plan.json
```

Both commands are local and side-effect free.

## Implementation hook

- `src/models/realtime_decision_handoff.py` owns reusable validators and route-plan builders.
- `scripts/models/plan_realtime_decision_handoff.py` emits route plans.
- `scripts/models/validate_realtime_decision_handoff.py` validates input snapshots or route plans.

Future work may add an explicit fixture/shadow generation executor that consumes this route plan. That executor must remain separate from production model activation and must register any shared names through `trading-manager` before cross-repository use.
