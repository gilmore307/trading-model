# trading-model docs

This docs tree is the canonical home for the `trading-model` repository documentation.

`trading-model` exists to build and improve an unsupervised market-state model using upstream data and strategy outputs.

Hard boundary:
- `trading-data` provides market and context data
- `trading-strategy` provides strategy-run outputs and evaluation surfaces
- `trading-model` uses those upstreams to discover market states first, then evaluate whether those states are useful for strategy selection

## Read in workflow order

1. `01-overview.md`
2. `02-inputs-workflow-and-boundary.md`
3. `03-discovery-evaluation-and-reporting.md`
4. `04-repo-structure-and-implementation-status.md`
5. `05-current-boundary-and-next-phase.md`
