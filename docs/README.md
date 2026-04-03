# trading-model docs

This repository exists to build and improve an **unsupervised market-state model** using upstream data and strategy outputs.

Hard boundary:
- `trading-data` provides market and context data
- `trading-strategy` provides strategy-run outputs and evaluation surfaces
- `trading-model` uses those upstreams to discover market states first, then evaluate whether those states are useful for strategy selection

## Read in workflow order

1. `01-overview.md`
2. `02-workflow.md`
3. `03-inputs-and-data-contracts.md`
4. `04-unsupervised-model.md`
5. `05-state-evaluation-and-policy-mapping.md`
6. `06-model-composite-and-reporting.md`
7. `07-repo-structure.md`
8. `08-current-status.md`

## Documentation rule

These docs should stay aligned with one core reality:
- market states are discovered from market-side data first
- strategy outputs are attached only after state discovery
- model quality is judged mainly by how much the model composite captures relative to the oracle composite
