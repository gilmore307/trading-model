# models

Model-specific implementation packages.

Each accepted model output/research boundary gets its own package under this directory. Keep model-local generators, evaluation harnesses, configs, evidence maps, and README files inside the model package unless a helper is genuinely shared across model layers.

Current packages:

- `model_01_market_regime/` — `MarketRegimeModel` V1 broad market-context state implementation.
- `model_02_sector_context/` — `SectorContextModel` V1 contract-first package for sector/industry context state.
- `model_03_target_state_vector/` — `TargetStateVectorModel` contract-first package for Layer 3 target state-vector construction.
- `model_03_strategy_selection/` — legacy frozen strategy-selection research workspace; do not expand as active Layer 3.

Shared governance/promotion helpers stay outside this directory in `src/model_governance/`.
