# trading-model

Historical research, feature/model development, parameter modeling, and backtest-focused upstream codebase.

This repository should retain:
- upstream data consumption from `trading-data`
- upstream strategy-output consumption from `trading-strategy`
- dataset construction and curation for research use
- market-state / regime research
- feature engineering and parameter utility modeling
- offline evaluation, selector/model building, and Oracle-gap analysis
- research reports, candidate outputs, and model artifacts

This repository should not be the canonical home for:
- upstream market-data acquisition
- source-adapter ownership
- ETF holdings extraction / refresh workflows
- live runtime execution

This repository is the upstream to:
- <https://github.com/gilmore307/quantitative-trading>

`trading-data` owns upstream market-data acquisition and context refresh.
`quantitative-trading` owns live runtime execution.
`trading-model` owns historical research, modeling, and promotion-candidate generation.

Project documentation lives under `docs/`.

Start here:
- `docs/README.md`
- `docs/01-overview.md`
- `docs/02-repo-structure.md`
- `docs/10-migration-status.md`
- `docs/14-data-source-boundary-and-model-scope.md`
- `docs/18-trading-data-handoff-and-research-object-classes.md`
- `TODO.md`
