# trading-model

`trading-model` is the repository for building and improving an **unsupervised market-state model**.

This repository must be built on two upstream inputs:
- `trading-data` supplies market and context data
- `trading-strategy` supplies strategy outputs and evaluation surfaces

`trading-model` uses those two upstream data sources to:
- build aligned modeling tables
- discover recurring market-state structure with unsupervised methods
- evaluate whether discovered states meaningfully separate strategy behavior
- improve the model continuously as new upstream data arrives

This repository does **not** own:
- raw data acquisition
- source adapters
- strategy execution ownership
- live runtime operations

Start with:
- `docs/README.md`
- `docs/01-overview.md`
- `docs/02-workflow.md`
- `docs/03-inputs-and-data-contracts.md`
- `docs/04-unsupervised-model.md`
- `docs/05-optimization-loop.md`
