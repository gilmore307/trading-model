# TODO

## Current repo-normalization work

- [x] reorganize the docs tree into a workflow-first active path
- [x] delete `docs/archive/`
- [x] delete in-repo `data/`
- [x] remove clearly out-of-scope runtime / execution / state / reconcile modules
- [x] remove clearly out-of-scope acquisition scripts and market-ingestion modules
- [x] remove `scripts/` and keep the repository centered on `src/`
- [x] remove stale tests that primarily targeted deleted runtime/acquisition code
- [ ] review remaining `src/runners/` and helpers for any residual repo-boundary leakage
- [ ] review `src/review/` and confirm every remaining module is strictly offline/historical
- [ ] review `src/research/runtime_adapters.py` and either rename, relocate, or remove it if it still implies runtime coupling
- [ ] review `src/config/` for any settings that belong in downstream runtime repos instead
- [ ] normalize remaining references from old hybrid assumptions to the current split

## Structural rules

- core docs use ordered workflow-oriented files under `docs/`
- source code in this repo should remain research/modeling-oriented
- keep implementation under `src/`
- do not reintroduce acquisition ownership or live runtime ownership here
