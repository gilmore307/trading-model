# models

Model-specific implementation packages.

Each accepted model output/research boundary gets its own package under this directory. Keep model-local generators, evaluation harnesses, configs, evidence maps, and README files inside the model package unless a helper is genuinely shared across model layers.

Current packages:

- `model_01_market_regime/` — `MarketRegimeModel` V2.2 broad market-context state implementation.
- `model_02_sector_context/` — `SectorContextModel` V1 contract-first package for sector/industry context state.
- `model_03_target_state_vector/` — Layer 3 package containing anonymous target candidate preprocessing contracts plus `TargetStateVectorModel` target-context/state-vector output contracts.
- `model_07_underlying_action/` — Layer 7 deterministic scaffold for `UnderlyingActionModel`, producing offline `underlying_action_plan` / `underlying_action_vector` rows and plan-quality labels without broker orders or option-contract selection.

Shared governance/promotion helpers stay outside this directory in `src/model_governance/`.
