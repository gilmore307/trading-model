# scripts

Executable wrappers for `trading-model` operational tasks.

- `generate_model_01_market_regime.py` reads `trading_data.feature_01_market_regime` and upserts the continuous state vector into `trading_model.model_01_market_regime`.
- `ensure_model_governance_schema.py` emits the generic `trading_model` governance/evaluation table DDL to local gitignored `storage/sql/model_governance_schema.sql` by default. It creates real database tables only when explicitly run with `--apply`.
- `evaluate_model_01_market_regime.py` runs a dry-run-only MarketRegimeModel evaluation harness. It creates in-memory governance/evaluation rows from fixture or local JSONL data and never connects to PostgreSQL.
