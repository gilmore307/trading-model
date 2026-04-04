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

## Control-plane responsibility migration to `trading-manager`

The new `trading-manager` repo will absorb part of the orchestration/storage-lifecycle responsibility that should not remain embedded inside `trading-model`.

### Migrate out of `trading-model`
- [ ] move cross-repo workflow sequencing around model runs into `trading-manager`
- [ ] move decisions about when a scope is ready to enter model-build/model-evaluation workflows into `trading-manager`
- [ ] move active-variant-set lifecycle control out of `trading-model`; `trading-model` should produce ranking/selection/pruning judgments, but `trading-manager` should own the durable control-plane state and orchestration around those decisions
- [ ] move survivor-floor / expansion-cycle orchestration into `trading-manager`
- [ ] move historical-scope rehydration orchestration for new-family/new-variant validation into `trading-manager`
- [ ] move storage lifecycle decisions for historical model outputs (hot vs cold archive vs delete) into `trading-manager`
- [ ] keep `trading-model` focused on offline modeling/evaluation logic, scoring/ranking outputs, and model-side artifact contracts

## Structural rules

- core docs use ordered workflow-oriented files under `docs/`
- source code in this repo should remain research/modeling-oriented
- keep implementation under `src/`
- do not reintroduce acquisition ownership or live runtime ownership here
- keep cross-repo orchestration/control-plane state out of this repo; `trading-manager` should own sequencing, scheduling, and storage-lifecycle decisions around model workflows
