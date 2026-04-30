# scripts

Executable wrappers for `trading-model` operational tasks.

- `generate_model_01_market_regime.py` reads `trading_data.feature_01_market_regime` and upserts the continuous state vector into `trading_model.model_01_market_regime`.
- `ensure_model_governance_schema.py` creates the generic `trading_model` governance/evaluation tables used by model dataset requests, snapshots, splits, labels, evaluation runs, and metrics.
- `evaluate_model_01_market_regime.py` runs a dry-run-only MarketRegimeModel evaluation harness. It creates in-memory governance/evaluation rows from fixture or local JSONL data and never connects to PostgreSQL.
