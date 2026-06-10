# Realtime Decision Handoff

Status: accepted route-plan boundary; no production activation
Date: 2026-06-10

## Purpose

Realtime execution capture can produce `execution_model_decision_input_snapshot` envelopes. `trading-model` needs a model-side entry boundary that accepts those envelopes for fixture/shadow routing into the historical model stack without accidentally activating production inference or execution.

This document defines that boundary for the current six-model stack.

## Accepted Chain

```text
trading-execution realtime capture
  -> realtime_feature_snapshot
  -> execution_model_decision_input_snapshot
  -> model_realtime_decision_route_plan
  -> fixture/shadow historical-model generation route
```

`model_realtime_decision_route_plan` is a route plan, not a model output. Its execution unit is the current model component, not the retired ten-layer route. It validates required M01-M04 and M06 component input refs, accepts M05 option-expression component refs when available, maps each present component to its reviewed generator entrypoint, and records the handoff mode. Direct-underlying routes must not require M05 option refs.

Accepted handoff modes:

- `fixture_replay`
- `shadow_monitoring`

## Required Input

The model-side planner consumes an `execution_model_decision_input_snapshot` object with:

- `decision_input_snapshot_id`
- `decision_time`
- `instrument_ref`
- `historical_dataset_snapshot_ref`
- `frozen_model_config_ref`
- `realtime_feature_snapshot_ref`
- `component_input_refs`
- exactly one required component input for M01-M04 and M06
- zero or one optional M05 option-expression component input

Each component input must include the expected model id, expected model output, feature ref, frozen model config ref, and historical dataset snapshot ref.

## Component Route Mapping

| Component | Model | Model id | Expected output | Invocation policy | Route entrypoint |
|---|---|---|---|---|---|
| `background_context_component` | `M01` | `background_context_model` | `background_context_state` | required | `scripts/models/model_01_background_context/generate_model_01_background_context.py` |
| `target_state_component` | `M02` | `target_state_model` | `target_context_state` | required | `scripts/models/model_02_target_state/generate_model_02_target_state.py` |
| `event_state_component` | `M03` | `event_state_model` | `event_state_vector` | required | `scripts/models/model_03_event_state/generate_model_03_event_state.py` |
| `unified_decision_component` | `M04` | `unified_decision_model` | `unified_decision_vector` | required decision component | `scripts/models/model_04_unified_decision/generate_model_04_unified_decision.py` |
| `option_expression_component` | `M05` | `option_expression_model` | optional `trading_guidance_record`, `option_expression_plan`, or `expression_vector` | conditional after M04 intent or option applicability | `scripts/models/model_05_option_expression/generate_model_05_option_expression.py` |
| `residual_event_governance_component` | `M06` | `residual_event_governance_model` | `event_risk_intervention` / future packet eligibility | required residual event governance component | `scripts/models/model_06_residual_event_governance/generate_model_06_residual_event_governance.py` |

Retired ten-layer route mappings are migration-source routes only.

## Training Versus Execution

Historical training and evaluation still preserve full-minute state coverage as defined in `docs/23_model_learning_design.md`. Live and replay execution may invoke components conditionally. For example, M04 can produce a no-trade or direct-underlying thesis without invoking the expensive M05 option-expression component, while the training ledger still records the minute's no-option or not-option-applicable state.

## Non-Authorizations

This boundary does not:

- open provider streams;
- read secrets;
- refit models;
- activate production model configs;
- produce a promoted production decision;
- construct broker orders;
- mutate broker/account state;
- persist manager-control-plane decisions.

It only plans and validates the component route from realtime input refs into the historical model stack. It may support the closed-loop evidence lifecycle by producing fixture/shadow route evidence, but any labels, utilities, residuals, or promotion feedback are joined only after fold or shadow-window settlement through the review-gated path in `docs/23_model_learning_design.md`.

## CLI

```bash
PYTHONPATH=src python3 scripts/models/plan_realtime_decision_handoff.py decision_input.json \
  --handoff-mode shadow_monitoring > route_plan.json

PYTHONPATH=src python3 scripts/models/validate_realtime_decision_handoff.py route_plan.json
```

Both commands are local and side-effect free.

## Implementation Hook

- `src/models/realtime_decision_handoff.py` owns reusable validators and route-plan builders.
- `scripts/models/plan_realtime_decision_handoff.py` emits route plans.
- `scripts/models/validate_realtime_decision_handoff.py` validates input snapshots or route plans.
