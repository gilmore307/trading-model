# model_02_sector_context

`SectorContextModel` package boundary.

Current status: direction-neutral baseline generator, SQL writer, evaluation path, and registry-backed field contract implemented for the accepted three-artifact contract. Treat the per-ETF Layer 2 state as `context_etf_state`.

Boundary:

- Input: `market_context_state`, `trading_data.m02_sector_context_feature_generation`, and ETF/basket tradability/event diagnostics available at or before `available_time`.
- Conceptual output: `context_etf_state` keyed by `available_time + context_etf_symbol`.
- Physical artifacts: `trading_model.m02_sector_context_model_generation`, `trading_model.m02_sector_context_model_generation_explainability`, and `trading_model.m02_sector_context_model_generation_diagnostics`.
- May emit sector-context eligibility, bias, and rank fields for downstream context attachment and audit.
- Target routing distinguishes Layer 1 ETF targets, Layer 2 context ETF targets, and ordinary targets with dynamic `target_context_profile` weighting.
- Per-ETF cross-section rows are construction evidence inside `context_etf_state`; only global/group `cross_etf_summary` should be separate.
- No final stock selection, strategy selection, entry timing, option contract selection, final size, or portfolio weighting.
- ETF holdings and `stock_etf_exposure` are standalone exposure evidence. They do not define Layer 2 behavior modeling, the realtime total pool, Layer 3 ordinary candidates, or historical replay candidates unless a later reviewed exposure contract explicitly asks for them.

Files:

- `sector_context_state_contract.md` — field contract and boundary rules.
- `generator.py` — baseline row generator for the primary output plus explainability and diagnostics support artifacts.

Runtime SQL writes are isolated in `scripts/models/model_02_sector_context/generate_model_02_sector_context.py`.

Promotion evidence is built by `evaluation.py` and `scripts/models/model_02_sector_context/evaluate_model_02_sector_context.py`. Promotion review is handled by `scripts/models/model_02_sector_context/review_sector_context_promotion.py`; fixture/local evidence should defer until real database evaluation evidence clears explicit direction-neutral thresholds, baseline/stability checks, long/short sector handoff quality, selected absolute-path relationship, and no-future-leak gates.
