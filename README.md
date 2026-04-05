# trading-model

`trading-model` is the repository for building and improving an **unsupervised market-state model**.

This repository must be built on two upstream inputs:
- `trading-data` supplies market and context data
- `trading-strategy` supplies strategy outputs and evaluation surfaces

`trading-model` uses those two upstream data sources to:
- discover recurring market states from market-side data
- attach strategy/oracle outcomes only after state discovery
- build state-conditional policy mappings
- construct model composites
- evaluate how closely the model composite approaches the oracle composite

This repository does **not** own:
- raw data acquisition
- source adapters
- strategy execution ownership
- live runtime operations
- canonical final report assembly once `trading-report` is active

Start with:
- `docs/README.md`
- `docs/01-overview.md`
- `docs/02-workflow.md`
- `docs/03-inputs-and-data-contracts.md`
- `docs/04-unsupervised-model.md`
- `docs/05-state-evaluation-and-policy-mapping.md`
- `docs/06-model-composite-and-reporting.md`

## Current implementation status

A fresh minimal code skeleton now exists under `src/trading_model/` and follows the current docs-first repo boundary:
- stage 1 loads market bars from `trading-data`
- computes base-only v1 features
- applies winsorization + robust scaling
- runs unsupervised clustering with GMM/KMeans selection over candidate `k`
- writes state table / model-selection / stability artifacts
- stage 2 loads variant returns + global oracle returns from `trading-strategy`
- attaches strategy/oracle rows onto discovered states
- computes a first winner-mapping artifact
- writes an initial oracle-gap report

Current entrypoint:
- `python -m trading_model.cli --symbol AAPL --data-month 2603 --strategy-month 2603`
