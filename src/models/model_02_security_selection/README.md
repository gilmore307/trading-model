# model_02_security_selection

`SecuritySelectionModel` V1 package boundary.

Current status: contract-first; implementation pending.

Boundary:

- Input: `market_context_state`, `trading_data.feature_02_security_selection`, sector/industry ETF holdings evidence, `stock_etf_exposure`, and ETF tradability/event diagnostics available at or before `available_time`.
- Conceptual output: `sector_context_state` keyed by `available_time + sector_or_industry_symbol`.
- Planned physical output: `trading_model.model_02_security_selection` unless implementation evidence forces a narrower name.
- No final stock selection, strategy selection, entry timing, option contract selection, final size, or portfolio weighting.

Files:

- `sector_context_state_contract.md` — V1 field contract and boundary rules.
