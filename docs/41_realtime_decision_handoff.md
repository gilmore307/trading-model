# Realtime Decision Handoff

Status: accepted route-plan boundary; no production activation
Date: 2026-06-10

## Purpose

Realtime execution capture can produce `execution_model_decision_input_snapshot` envelopes. `trading-model` needs a model-side entry boundary that accepts those envelopes for fixture/shadow routing into the historical model stack without accidentally activating production inference or execution.

This document defines that boundary for the current five-model stack.

## Accepted Chain

```text
trading-execution realtime capture
  -> realtime_feature_snapshot
  -> execution_model_decision_input_snapshot
  -> model_realtime_decision_route_plan
  -> fixture/shadow historical-model generation route
```

`model_realtime_decision_route_plan` is a route plan, not a model output. Its execution unit is the accepted execution runtime component (`C01`, `C02`, and so on), not a retired serial route and not a model contract renamed as a component. It validates required runtime-component input refs, records the current M01-M05 model surfaces each component may need, and records the handoff mode. Direct-underlying routes must not require M05 option-expression refs; C04 Expression Review may emit a direct-underlying pass-through or structural no-option state.

The execution-side `runtime_component_manifest` is the authoritative component
catalog for this handoff. `trading-model` validates the manifest carried by the
snapshot and derives component route metadata from it; it does not own a
separate component graph.

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
- `runtime_component_manifest`
- `component_input_refs`
- exactly one required component input for `C01`, `C02`, `C03`, `C05`, and `C06`
- zero or one optional component input for `C04` and `C07`

Each component input must include the execution `component_id`, feature ref, frozen model config ref, and historical dataset snapshot ref. It may also declare the required and optional current model surfaces for validation.

## Component Route Mapping

| Runtime component | Required model surfaces | Optional model surfaces | Invocation policy |
|---|---|---|---|
| `component_01_intake` / `C01 Intake` | `model_01_background_context`, `model_02_target_state` | none | required runtime component |
| `component_02_entry` / `C02 Entry` | `model_03_event_state`, `model_04_unified_decision` | none | required for candidate entries |
| `component_03_lifecycle` / `C03 Lifecycle` | `model_03_event_state`, `model_04_unified_decision` | none | required for open positions |
| `component_04_expression_review` / `C04 Expression Review` | none | `model_05_option_expression` | conditional for optionable routes, held options, or direct-underlying pass-through |
| `component_05_order_intent` / `C05 Order Intent` | none | none | required after an accepted entry, lifecycle, or option decision |
| `component_06_execution_gate` / `C06 Execution Gate` | none | none | required before live or replay execution adapter |
| `component_07_failure_review` / `C07 Failure Review` | none | none | conditional after observed failure, deviation, or residual event risk |

Historical retired serial route mappings are not current realtime route contracts.

## Training Versus Execution

Historical training and evaluation still preserve full-minute state coverage as defined in `docs/23_model_learning_design.md`. Live and replay execution may invoke C-components conditionally. For example, C02 can receive an M04 no-trade or direct-underlying thesis without invoking C04/M05 option review, while the training ledger still records structural no-option or temporary option-chain-missing state.

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
