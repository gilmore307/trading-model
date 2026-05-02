# models

Model-specific implementation packages.

Each accepted model output/research boundary gets its own package under this directory. Keep model-local generators, evaluation harnesses, configs, evidence maps, and README files inside the model package unless a helper is genuinely shared across model layers.

Current packages:

- `model_01_market_regime/` — `MarketRegimeModel` V1 broad market-context state implementation.

Shared governance/promotion helpers stay outside this directory in `src/model_governance/`.
