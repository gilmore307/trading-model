# models

Model-specific implementation packages.

Each accepted model output/research boundary gets its own package under this directory. Keep model-local generators, evaluation harnesses, configs, evidence maps, and README files inside the model package unless a helper is genuinely shared across model layers.

Current packages:

- `model_01_market_regime/` — `MarketRegimeModel` V2.2 broad market-context state implementation.
- `model_02_sector_context/` — `SectorContextModel` V1 contract-first package for sector/industry context state.
- `model_03_target_state_vector/` — Layer 3 package containing anonymous target candidate preprocessing contracts plus `TargetStateVectorModel` target-context/state-vector output contracts.
- `model_04_event_failure_risk/` — current package for conceptual Layer 4 `EventFailureRiskModel`, producing reviewed event-failure conditioning rows without raw-event promotion, alpha, action, option, or execution leakage.
- `model_05_alpha_confidence/` — current package for conceptual Layer 5 `AlphaConfidenceModel`, producing adjusted `alpha_confidence_vector` rows plus base-alpha diagnostics and offline alpha labels without position/action leakage.
- `model_06_position_projection/` — current package for conceptual Layer 6 `PositionProjectionModel`, producing `position_projection_vector` rows and offline utility labels without action/execution leakage.
- `model_07_underlying_action/` — current package for conceptual Layer 7 `UnderlyingActionModel`, producing offline `underlying_action_plan` / `underlying_action_vector` rows and plan-quality labels without broker orders or option-contract selection.
- `model_08_option_expression/` — current package for conceptual Layer 8 `OptionExpressionModel` / trading-guidance option-expression work, producing offline `option_expression_plan` / `expression_vector` rows and option-expression labels without broker orders or account mutation.
- `model_09_event_risk_governor/` — conceptual Layer 9 deterministic scaffold for `EventRiskGovernor`, producing point-in-time event-risk context/intervention rows and offline event-overlay labels without alpha/action leakage.

Shared governance/promotion helpers stay outside this directory in `src/model_governance/`.
