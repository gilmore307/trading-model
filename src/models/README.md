# models

Model-specific implementation packages.

Each accepted model output/research boundary gets its own package under this directory. Keep model-local generators, evaluation harnesses, configs, evidence maps, and README files inside the model package unless a helper is genuinely shared across model contracts.

Current packages:

- `model_sequence.py` — serializable `M01` through `M06` display/order metadata for the current model stack.
- `model_01_background_context/` — `M01 Background Context`, broad market plus sector/industry background state.
- `model_02_target_state/` — `M02 Target State`, target eligibility, ranking, and anonymous target-state evidence.
- `model_03_event_state/` — `M03 Event State`, accepted event-state conditioning without event-parameter mutation.
- `model_04_unified_decision/` — `M04 Unified Decision`, structured edge/risk/exposure/action heads in one direct-underlying decision contract.
- `model_05_option_expression/` — `M05 Option Expression`, optional option/underlying expression after direct-underlying intent exists.
- `model_06_residual_event_governance/` — `M06 Residual Event Governance`, missed-event checks, residual intervention, attribution, and future event-family evidence.
- `return_distribution_surface/` — shared pilot utilities for the tradable-time conditional return distribution surface that M01 through M05 will progressively adopt.

Shared governance/promotion helpers stay outside this directory in `src/model_governance/`.
