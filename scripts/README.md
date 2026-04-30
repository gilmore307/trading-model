# scripts

Executable wrappers for `trading-model` operational tasks.

- `generate_model_01_market_regime.py` reads `trading_data.feature_01_market_regime` and upserts the continuous state vector into `trading_model.model_01_market_regime`.
- `ensure_model_governance_schema.py` creates the generic `trading_model` governance/evaluation/promotion tables through `psql`. Use `--dry-run` to print DDL without touching PostgreSQL.
- `clear_model_development_database.py` clears the `trading_model` development schema through `psql` after a development run. It requires an explicit confirmation token unless run with `--dry-run`.
- `evaluate_model_01_market_regime.py` runs a dry-run-only MarketRegimeModel evaluation harness. It creates in-memory governance/evaluation rows from fixture or local JSONL data and never connects to PostgreSQL.
