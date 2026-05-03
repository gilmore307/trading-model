# scripts

Executable wrappers and operational entrypoints for `trading-model`.

Directory boundary:

- `models/` owns model-specific entrypoints, organized by model package.
- `model_governance/` owns shared governance/development schema entrypoints that are not specific to one model.

Current model-specific entrypoints:

- `models/model_01_market_regime/generate_model_01_market_regime.py` reads `trading_data.feature_01_market_regime`, upserts the continuous state vector into `trading_model.model_01_market_regime`, and writes generic support artifacts to `trading_model.model_01_market_regime_explainability` and `trading_model.model_01_market_regime_diagnostics` by default.
- `models/model_01_market_regime/evaluate_model_01_market_regime.py` runs the MarketRegimeModel evaluation harness. By default it uses fixture/local JSONL dry-run evidence; with `--from-database` it performs a read-only SQL evaluation over real `trading_data` / `trading_model` rows and emits promotion evidence with explicit threshold results.
- `models/model_01_market_regime/run_market_regime_development_smoke.py` runs a deterministic development DB smoke test for `source_01_market_regime -> feature_01_market_regime -> model_01_market_regime -> evaluation`. It calls no providers and cleans its development tables by default.
- `models/model_01_market_regime/review_market_regime_promotion.py` builds an evaluation-backed promotion candidate and asks an OpenClaw agent to review whether it can be promoted. By default it prints review/decision rows only; with `--write-decision` it can persist the reviewed evidence, config, candidate, and decision rows, and with `--activate-approved-config` it can activate only accepted approval decisions by marking the reviewed config active.

Current shared governance entrypoints:

- `model_governance/ensure_model_governance_schema.py` creates the generic `trading_model` governance/evaluation/promotion tables through `psql`. Use `--dry-run` to print DDL without touching PostgreSQL.
- `model_governance/clear_model_development_database.py` clears the `trading_model` development schema through `psql` after a development run. It requires an explicit confirmation token unless run with `--dry-run`.
