# model_03_strategy_selection

Contract-first workspace for `StrategySelectionModel` / Layer 3.

Layer 3 scores which standalone strategy family and parameter-neighborhood variant fits an anonymous target candidate under current market and sector context. It does not own final entry/exit prices, option contract selection, position size, execution policy, or portfolio allocation.

Key files:

- `strategy_family_catalog.md` — reviewed strategy-family summary, suitable trading periods, parameter gradients, variant counts, and implementation notes.
- `strategy_idea_universe.md` — broader strategy idea registry for future backlog, moved boundaries, option-expression ideas, event overlays, and deferred ML/RL targets.

Current status: design/catalog only; implementation pending.
