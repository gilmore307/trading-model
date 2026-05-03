# model_02_sector_context

`SectorContextModel` V1 package boundary.

Current status: V1 deterministic generator and SQL writer implemented for the accepted three-artifact contract.

Boundary:

- Input: `market_context_state`, `trading_data.feature_02_sector_context`, and ETF/basket tradability/event diagnostics available at or before `available_time`.
- Conceptual output: `sector_context_state` keyed by `available_time + sector_or_industry_symbol`.
- Physical artifacts: `trading_model.model_02_sector_context`, `trading_model.model_02_sector_context_explainability`, and `trading_model.model_02_sector_context_diagnostics`.
- May mark sector/industry baskets as eligible/selected for downstream candidate construction.
- No final stock selection, strategy selection, entry timing, option contract selection, final size, or portfolio weighting.
- ETF holdings and `stock_etf_exposure` belong to the downstream anonymous target candidate builder / Layer 3 input preparation, not Layer 2 core behavior modeling.

Files:

- `sector_context_state_contract.md` — V1 field contract and boundary rules.
- `generator.py` — deterministic V1 row generator for the primary output plus explainability and diagnostics support artifacts.

Runtime SQL writes are isolated in `scripts/models/model_02_sector_context/generate_model_02_sector_context.py`.

Promotion evidence is built by `evaluation.py` and `scripts/models/model_02_sector_context/evaluate_model_02_sector_context.py`. Promotion review is handled by `scripts/models/model_02_sector_context/review_sector_context_promotion.py`; fixture/local evidence should defer until real database evaluation evidence clears explicit thresholds, baseline/stability checks, sector handoff quality, and no-future-leak gates.
