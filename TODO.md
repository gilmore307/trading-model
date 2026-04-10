# TODO

## Current repo-normalization work

- [x] reorganize the docs tree into a workflow-first active path
- [x] delete `docs/archive/`
- [x] delete in-repo `data/`
- [x] remove clearly out-of-scope runtime / execution / state / reconcile modules
- [x] remove clearly out-of-scope acquisition scripts and market-ingestion modules
- [x] remove `scripts/` and keep the repository centered on `src/`
- [x] remove stale tests that primarily targeted deleted runtime/acquisition code
- [x] review remaining `src/runners/` and helpers for any residual repo-boundary leakage
- [x] review `src/review/` and confirm every remaining module is strictly offline/historical
- [x] review `src/research/runtime_adapters.py` and either rename, relocate, or remove it if it still implies runtime coupling
- [x] review `src/config/` for any settings that belong in downstream runtime repos instead
- [x] normalize remaining references from old hybrid assumptions to the current split

## Control-plane responsibility migration to `trading-manager`

The new `trading-manager` repo will absorb part of the orchestration/storage-lifecycle responsibility that should not remain embedded inside `trading-model`.

Current migration status:
- first manager-side model request generation is implemented
- first manager-side model workflow/control-plane bridge is implemented
- active-variant-set control now lives in `trading-manager`
- pruning-decision / rerun-gating / expansion-plan / expansion-candidate control now lives in `trading-manager`
- survivor-floor / rehydration / archive-lifecycle first control-plane objects now live in `trading-manager`
- `trading-model` is now materially operating as the offline scoring/evaluation repo rather than the orchestration owner

### Migrate out of `trading-model`
- [x] move cross-repo workflow sequencing around model runs into `trading-manager`
- [x] move decisions about when a scope is ready to enter model-build/model-evaluation workflows into `trading-manager`
- [x] move active-variant-set lifecycle control out of `trading-model`; `trading-model` should produce ranking/selection/pruning judgments, but `trading-manager` should own the durable control-plane state and orchestration around those decisions
- [~] move survivor-floor / expansion-cycle orchestration into `trading-manager`
  - [x] expansion-cycle admission/enqueue now exists in `trading-manager`
  - [x] first bounded convergence-cycle command now exists in `trading-manager`
  - [x] first bounded multi-cycle stop policy now exists in `trading-manager`
  - [x] first explicit manager-owned survivor-floor rule/artifact now exists
  - [x] first convergence-time survivor-floor enforcement hook now exists in `trading-manager`
  - [ ] richer survivor-floor policy still remains
- [x] move historical-scope rehydration orchestration for new-family/new-variant validation into `trading-manager`
  - [x] first manager-owned rehydration request artifact/command now exists
  - [x] first manager-owned fulfillment flow now exists
- [x] move storage lifecycle decisions for historical model outputs (hot vs cold archive vs delete) into `trading-manager`
  - [x] first manager-owned archive decision artifact/command now exists
  - [x] first manager-owned fulfillment flow now exists
- [x] keep `trading-model` focused on offline modeling/evaluation logic, scoring/ranking outputs, and model-side artifact contracts

## Attach / reporting fidelity follow-ups

- [~] tighten attach audit fidelity for strategy/oracle alignment
  - [x] attach tables now expose explicit delta / abs-delta / tolerance / match-direction fields
  - [x] oracle-gap attach audit now reports status counts, direction counts, tolerance, and delta ranges
  - [ ] validate exact-vs-previous-bar semantics against richer upstream timestamp patterns

## Symbol-role / market-context boundary follow-ups

- [ ] when the five core broad-market ETFs (`SPY`, `QQQ`, `DIA`, `IWM`, `RSP`) are promoted into direct model research targets, exclude the target ETF itself from the market-regime/context feature bundle for that run
  - these five can serve either as regime/context proxies or as direct research targets depending on workflow stage
  - once one of them is the model target, it should no longer also appear inside the upstream "market state" evidence used to characterize that same target
  - implement this as a model-side feature/boundary rule rather than as a regime-universe membership flag
  - define the exact exclusion behavior in the model input contract before broadening direct research coverage for these symbols

## Model-output contract follow-ups

- [x] add a first standardized execution-facing confidence field to model outputs
  - current field: `execution_confidence`
  - current companion field: `opportunity_strength`
  - current semantics: ranking strength for a state-routed winner decision, not calibrated probability of success
  - current numeric range: `[0.0, 1.0]`
  - exposed in winner-mapping artifacts and downstream-facing report summaries
- [ ] calibrate and validate the execution-facing confidence contract empirically
  - test monotonicity vs realized downstream utility / sizing outcomes
  - decide whether downstream should ultimately consume `execution_confidence`, `opportunity_strength`, or both
  - refine weighting / calibration once broader cross-symbol and multi-month evidence exists

## Storage / artifact structure follow-ups

- [x] partition large model artifacts into bounded downstream slices
  - [x] state tables are partitioned by `symbol / month`
  - [x] model selection is partitioned by `symbol / state_model_version`
  - [x] stability reports are partitioned by `symbol / state_model_version`
  - [x] state-evaluation tables are partitioned by `symbol / family / variant / month`
  - [x] winner mappings are partitioned by `symbol / mapping_version`
  - [x] trivial-baseline policy outputs are partitioned by `symbol / trivial_baseline_id`
  - [x] oracle-gap summary/report surfaces now have partitioned outputs
  - [x] multi-symbol summary / aggregate verdict now have partitioned outputs
  - [x] partition keys are now chosen by artifact-specific semantics and lifecycle needs, not by a fixed dimension template
  - [x] partition writers enforce a max single-file target of `<= 50 MB`
  - [x] oversize partitions auto-split into additional chunk files under the same partition path
  - partitioned artifacts are the canonical machine-facing contract
  - large top-level aggregate tables are no longer part of the intended output contract
  - only compact top-level summary/judgment outputs should remain as convenience/debug artifacts
  - derived datasets should follow the same storage discipline as upstream market data where practical
  - outputs should be appendable and deletable in bounded slices rather than single huge files
- [x] delete any remaining in-repo logic that writes raw market data under `data/raw/*`
  - current minimal pipeline reads prepared market data from `trading-data`
  - no active in-repo raw-market write path is present in the current codebase
  - this repo must not reacquire or persist raw market feeds as its own storage responsibility
- [x] clarify the final canonical artifact contract for downstream consumers
  - partitioned outputs are the canonical downstream contract
  - top-level monolithic outputs remain convenience/debug artifacts unless explicitly retired
  - keep model-side artifact layout aligned with manager-owned lifecycle control
- [ ] refine Git-friendly artifact policy beyond single-file partitioning
  - single-file caps alone are not sufficient if total pushed artifact mass is still too large
  - decide which heavy derived partitions should stay rebuildable/local rather than tracked in GitHub
  - keep compact verdict/mapping/summary artifacts easy to push while avoiding repeated pack-object blowups
- [x] simplify multi-symbol summary outputs
  - `multi_symbol_summary.json` is the canonical whole-object summary
  - per-symbol partitioned summary rows remain available as a convenience/index layer
  - separate top-level `multi_symbol_summary.csv` and `aggregate_cross_symbol_verdict.json` are no longer necessary

## Structural rules

- core docs use ordered workflow-oriented files under `docs/`
- source code in this repo should remain research/modeling-oriented
- keep implementation under `src/`
- do not reintroduce acquisition ownership or live runtime ownership here
- keep cross-repo orchestration/control-plane state out of this repo; `trading-manager` should own sequencing, scheduling, and storage-lifecycle decisions around model workflows
