# trading-model

Historical research, feature/model development, selector/model research, and promotion-candidate generation upstream for the trading system.

This repository should retain:
- upstream data consumption from `trading-data`
- upstream strategy-output consumption from `trading-strategy`
- research-side dataset construction and curation
- market-state / regime research
- feature engineering and parameter utility modeling
- offline evaluation, selector/model building, and Oracle-gap analysis
- research reports, candidate outputs, and model artifacts

This repository should not be the canonical home for:
- upstream market-data acquisition
- source-adapter ownership
- ETF holdings extraction / refresh workflows
- live runtime execution
- exchange-connected execution/reconcile/state management

This repository is the upstream to:
- <https://github.com/gilmore307/quantitative-trading>

Role split:
- `trading-data` owns upstream market-data acquisition and context refresh
- `trading-strategy` owns strategy execution-layer outputs for research consumption
- `trading-model` owns historical research, modeling, and promotion-candidate generation
- `quantitative-trading` owns live runtime execution

Project documentation lives under `docs/`.
Core implementation lives under `src/`.

Start here:
- `docs/README.md`
- `docs/01-overview.md`
- `docs/02-workflow.md`
- `docs/03-inputs-and-data-contracts.md`
- `docs/06-strategy-research.md`
- `docs/07-promotion-and-output-boundary.md`
- `TODO.md`
