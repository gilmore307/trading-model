# trading-model docs

This repository exists to build and improve an **unsupervised market-state model** using data provided by upstream repositories.

Hard boundary:
- `trading-data` provides market and context data
- `trading-strategy` provides strategy-run outputs and evaluation surfaces
- `trading-model` consumes those upstream datasets to build market-state recognition models and improve them over time

`trading-model` does **not** own raw data acquisition, source adapters, strategy execution, or live runtime operations.

## Read in order

1. `01-overview.md`
2. `02-workflow.md`
3. `03-inputs-and-data-contracts.md`
4. `04-unsupervised-model.md`
5. `05-optimization-loop.md`
6. `06-output-boundary.md`
7. `07-repo-structure.md`
8. `08-current-status.md`

## Documentation rule

These docs should stay aligned with one core reality:
- upstream data comes from `trading-data`
- upstream strategy outputs come from `trading-strategy`
- this repo builds and improves the unsupervised market-state model on top of those inputs
