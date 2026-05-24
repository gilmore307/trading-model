# models

Model-specific implementation packages.

Each accepted model output/research boundary gets its own package under this directory. Keep model-local generators, evaluation harnesses, configs, evidence maps, and README files inside the model package unless a helper is genuinely shared across model layers.

Current packages:

- `model_sequence.py` — serializable `M01` through `M10` display/order metadata for the current model stack.
- `model_01_market_regime/` — `M01 Market Regime`, V2.2 broad market-context state implementation.
- `model_02_sector_context/` — `M02 Sector Context`, V1 contract-first package for sector/industry context state.
- `model_03_target_state_vector/` — `M03 Target State`, anonymous target candidate preprocessing contracts plus `TargetStateVectorModel` target-context/state-vector output contracts.
- `model_04_event_failure_risk/` — `M04 Event Failure Risk`, producing reviewed event-failure conditioning rows without raw-event promotion, alpha, action, option, or execution leakage.
- `model_05_alpha_confidence/` — `M05 Alpha Confidence`, producing adjusted `alpha_confidence_vector` rows plus base-alpha diagnostics and offline alpha labels without position/action leakage.
- `model_06_dynamic_risk_policy/` — `M06 Dynamic Risk Policy`, producing model-internal `dynamic_risk_policy_state` rows without broker permission or hard execution limits.
- `model_07_position_projection/` — `M07 Position Projection`, producing `position_projection_vector` rows and offline utility labels without action/execution leakage.
- `model_08_underlying_action/` — `M08 Underlying Action`, producing offline `underlying_action_plan` / `underlying_action_vector` rows and plan-quality labels without broker orders or option-contract selection.
- `model_09_option_expression/` — `M09 Option Expression`, trading-guidance option-expression work producing offline `option_expression_plan` / `expression_vector` rows and option-expression labels without broker orders or account mutation.
- `model_10_event_risk_governor/` — `M10 Event Risk Governor`, producing point-in-time event-risk context/intervention rows and offline event-overlay labels without alpha/action leakage.

Shared governance/promotion helpers stay outside this directory in `src/model_governance/`.
