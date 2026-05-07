# models

Model-specific implementation packages.

Each accepted model output/research boundary gets its own package under this directory. Keep model-local generators, evaluation harnesses, configs, evidence maps, and README files inside the model package unless a helper is genuinely shared across model layers.

Current packages:

- `model_01_market_regime/` — `MarketRegimeModel` V2.2 broad market-context state implementation.
- `model_02_sector_context/` — `SectorContextModel` V1 contract-first package for sector/industry context state.
- `model_03_target_state_vector/` — Layer 3 package containing anonymous target candidate preprocessing contracts plus `TargetStateVectorModel` target-context/state-vector output contracts.
- `model_04_event_overlay/` — Layer 4 deterministic scaffold for `EventOverlayModel`, producing point-in-time `event_context_vector` rows and offline event-overlay labels without alpha/action leakage.
- `model_05_alpha_confidence/` — Layer 5 deterministic scaffold for `AlphaConfidenceModel`, producing adjusted `alpha_confidence_vector` rows plus base-alpha diagnostics and offline alpha labels without position/action leakage.
- `model_06_position_projection/` — Layer 6 deterministic scaffold for `PositionProjectionModel`, producing `position_projection_vector` rows and offline utility labels without action/execution leakage.
- `model_07_underlying_action/` — Layer 7 deterministic scaffold for `UnderlyingActionModel`, producing offline `underlying_action_plan` / `underlying_action_vector` rows and plan-quality labels without broker orders or option-contract selection.
- `model_08_option_expression/` — Layer 8 deterministic scaffold for `OptionExpressionModel`, producing offline `option_expression_plan` / `expression_vector` rows and option-expression labels without broker orders or account mutation.

Shared governance/promotion helpers stay outside this directory in `src/model_governance/`.
