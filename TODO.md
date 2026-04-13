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
- [ ] add a crypto-research feature path that can use regime ETF proxies (`IBIT`, `ETHA`, `FSOL`, and similar crypto-linked ETF/context symbols) to help study crypto targets when direct crypto microstructure coverage is incomplete
  - this is a model-side research/input question, not a market-tape completion-contract question
  - treat these ETF series as optional explanatory context for crypto modeling rather than as a substitute for the direct target's own required market-tape artifacts
  - define when crypto-linked ETF context should be included, how it should be aligned in time, and how to avoid leaking target-proxy duplication into feature construction
- [ ] formalize the three-layer model stack and its data-consumption boundaries
  - `market_state_model`: use regime/context data to identify market state and highlight unusually favorable sectors / symbols
  - `strategy_selection_model`: take candidate targets plus market-state outputs and select entry/exit strategy style
  - `option_selection_model`: once trade direction/timing is fixed, choose option parameters / expression templates to maximize payoff / control risk
  - boundary rule: treat upstream trade intent validity as a prerequisite; if the strategy itself is wrong, that is outside the option-selection model's research scope
  - still allow the option-selection model to reject option expression for a valid trade intent when liquidity / spread / theta / IV structure makes options unattractive
  - first research direction: mirror the `trading-model` family-selection pattern by defining a small set of option execution strategy templates, backtesting them under valid trade intents, and ranking the templates by market-state/trade-intent context instead of jumping directly to unconstrained per-contract optimization
- [ ] formalize option-chain data consumption as a two-surface model contract
  - preserve a rich underlying option-chain raw layer for the dedicated `option_selection_model`
  - separately derive an underlying-level compressed `option_chain_context` surface for `market_state_model` and `strategy_selection_model`
  - do not force earlier model layers to ingest the full contract-by-contract chain directly
  - current research direction for raw option collection to support this:
    - Friday expiries only (ignore non-Friday expiries for the first mainline)
    - organize by expiry cohort rather than observation month semantics
    - use expiry-month folder -> expiry-week/date folder -> one contract per file
    - use call/put ATM±5 strike ladders around an anchor underlying price for the selected expiry cohort
    - first expiry policy direction: focus on a ~4-week Friday expiry cohort rather than the nearest weekly expiry; use a DTE-band style rule internally when formalized
    - because the option universe is now intentionally narrowed to a single farther expiry cohort plus a limited strike ladder, keep the first canonical intraday grain at `1m`
- [ ] define the first compressed option-chain context feature set for underlying research
  - likely first-wave groups: IV term structure, skew, open-interest/volume structure, and liquidity/spread context
  - treat this as a model-input contract question rather than a storage minimization question
  - align the compressed feature contract with the new raw-collection assumption that expiry cohorts are the primary option-domain sampling unit, not generic calendar months

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
