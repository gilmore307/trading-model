# scripts

Executable wrappers and operational entrypoints for `trading-model`.

Directory boundary:

- `models/` owns model-specific entrypoints, organized by model package.
- `model_governance/` owns shared governance/development schema entrypoints that are not specific to one model.

Current model-specific entrypoints:

- `models/model_01_market_regime/generate_model_01_market_regime.py` reads `trading_data.feature_01_market_regime` and upserts the continuous state vector into `trading_model.model_01_market_regime`.
- `models/model_01_market_regime/evaluate_model_01_market_regime.py` runs a dry-run-only MarketRegimeModel evaluation harness. It creates in-memory governance/evaluation rows from fixture or local JSONL data and never connects to PostgreSQL.
- `models/model_01_market_regime/run_market_regime_development_smoke.py` runs a deterministic development DB smoke test for `source_01_market_regime -> feature_01_market_regime -> model_01_market_regime -> evaluation`. It calls no providers and cleans its development tables by default.
- `models/model_01_market_regime/review_market_regime_promotion.py` builds an evaluation-backed promotion candidate and asks an OpenClaw agent to review whether it can be promoted. It emits review/decision rows only; it does not write promotion decisions or change a production pointer.

Current shared governance entrypoints:

- `model_governance/ensure_model_governance_schema.py` creates the generic `trading_model` governance/evaluation/promotion tables through `psql`. Use `--dry-run` to print DDL without touching PostgreSQL.
- `model_governance/clear_model_development_database.py` clears the `trading_model` development schema through `psql` after a development run. It requires an explicit confirmation token unless run with `--dry-run`.
