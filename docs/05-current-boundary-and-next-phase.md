# 05 Current Boundary and Next Phase

This document summarizes the current control-plane boundary and the remaining next-phase work.

## Current migration status

Already moved to `trading-manager`:
- model request generation
- model workflow/control-plane bridge
- active-variant-set control
- pruning-decision / rerun-gating / expansion-plan / expansion-candidate control
- survivor-floor / rehydration / archive-lifecycle first control-plane objects

`trading-model` is now materially operating as the offline scoring/evaluation repo rather than the orchestration owner.

## What stays here
- offline modeling/evaluation logic
- scoring/ranking outputs
- model-side artifact contracts
- research reporting

## Remaining next-phase work
- add an explicit model-side symbol-role boundary for the five core broad-market ETFs (`SPY`, `QQQ`, `DIA`, `IWM`, `RSP`)
  - when one of these ETFs is itself the direct model target, the market-regime/context bundle for that run should exclude that same ETF from the context set
  - this avoids letting a symbol act as both the target under study and part of its own market-state context definition in the same modeling pass
  - keep this rule in the model input / feature-boundary layer rather than pushing it back into regime-universe metadata
- add a model-side crypto research path that can incorporate crypto-linked regime ETF proxies such as `IBIT`, `ETHA`, `FSOL`, and related symbols as optional explanatory context for crypto targets
  - this belongs to the model/input layer because the question is how to use proxy context to improve crypto research, not how to redefine direct market-tape completion contracts
  - these ETF/proxy series should be treated as context features, not as replacements for the target symbol's own required retained artifacts
  - later work should define inclusion rules, anti-duplication guards, and temporal alignment rules for mixing direct crypto target data with proxy ETF context
- richer survivor-floor policy in `trading-manager`
- richer symbol-aware oscillation policy in `trading-manager`
- deeper threshold calibration and reporting refinement here
- continue tightening attach audit fidelity here
  - keep exact / previous-bar / out-of-tolerance / missing semantics explicit in both table fields and report summaries
  - preserve attach-direction and absolute-delta diagnostics so timestamp alignment quality stays inspectable
- broader multi-month empirical validation after expansion-driven upstream coverage increases
- calibrate the new execution-facing confidence / opportunity-strength field empirically
  - current contract is `execution_confidence` in `[0.0, 1.0]`
  - current semantics are ranking strength for state-routed selection, not calibrated probability
  - current reporting now surfaces confidence summaries in winner mappings, research verdicts, oracle-gap by-state outputs, and multi-symbol summaries
  - later work should validate monotonicity against realized downstream utility and sizing outcomes
- continue refining partition policy where empirical use suggests better keys or report slicing
  - the active pipeline now writes partitioned state/state-evaluation/mapping/baseline outputs plus partitioned report/summary artifacts
  - future changes should be artifact-specific rather than template-driven
  - large appendable tables should keep getting the most aggressive semantic partitioning
  - small versioned judgment objects and global summaries should only be further split when a real consumer/lifecycle need exists
- add a Git-friendly artifact policy on top of partitioning
  - partitioning solves single-file blowups but does not automatically solve total push/package mass
  - decide which heavy derived partitions should remain rebuildable/local instead of tracked in GitHub
  - keep compact research verdict / mapping / summary outputs easy to version and push
- keep the raw-market-data boundary enforced
  - market acquisition and raw-market persistence belong in `trading-data`
  - current minimal pipeline does not write in-repo raw-market stores
  - future work should avoid reintroducing any `data/raw/*` write path here
- clarify the final canonical artifact contract for downstream consumers
  - decide which top-level outputs remain convenience/debug artifacts
  - decide which partitioned outputs are the canonical downstream contract
  - keep model-side layout stable for manager-owned lifecycle handling
- any future execution-layer integration after `trading-execution` is ready
