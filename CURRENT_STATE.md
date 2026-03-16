# CURRENT_STATE

_Last updated: 2026-03-17 01:57 Asia/Shanghai_

## Current session focus

This session returned to the crypto-trading runtime line and focused on three operational goals:

1. replace the crowded account API credentials locally
2. investigate why the trade daemon stopped / why routing was freezing
3. harden the runtime reconciliation path and re-enable direct Discord notifications from the daemon itself

## What was completed this session

### 1. Crowded account API credentials updated locally
- crowded API key / secret / passphrase were updated in project `.env`
- crowded account label was explicitly reverted to remain `Crowded`
- no external account-side changes were made from the codebase; this was local config only

### 2. Trade daemon / runtime status investigation
Findings from live repo/log inspection:
- daemon was **not** running at session start
- historical daemon runs were not under systemd supervision
- prior long runs showed `daemon_started` without matching `daemon_stopped` or `cycle_error`, which strongly suggested process/session loss rather than an application-level clean exit
- the system could still start and complete bounded runs successfully

### 3. Direct Discord notification path completed
Implemented and validated:
- repo-local direct Discord notifier via webhook / bot token support
- trade daemon now notifies directly instead of depending on the old watcher polling path
- direct notify includes de-duplication state to reduce repeated alerts
- default behavior now emphasizes critical events:
  - accepted enter/exit trade notifications
  - cycle errors
  - severe alignment / freeze-route conditions
- webhook was configured locally and a standalone test message was successfully delivered

### 4. Reconciliation hardening work shipped
A mismatch/freeze root-cause analysis identified three interacting causes:
- local `size` semantics not matching exchange `contracts`
- verify/reconcile using stale pre-submit exchange snapshots
- live state / route state being in-memory only and lost across restarts

Changes implemented and pushed:
- record local submitted position size from execution receipt size when available, instead of blindly using raw plan size
- refresh exchange snapshot after submit before verification / reconciliation
- persist live position state to disk
- persist route registry state to disk
- add regression tests for state persistence and refreshed entry flow

## Git / code state landed
Pushed this session:
- `3de2713` — `Add direct Discord notifications for trade daemon`
- `8c84ed1` — `Harden runtime state reconciliation`

## Runtime state at closeout
- daemon was started successfully during this session and confirmed running in background
- immediately after restart, first live cycle still reported:
  - `symbol = BTC-USDT-SWAP`
  - `regime = trend`
  - `plan_action = hold`
  - `block_reason = severe_alignment_issue`
  - diagnostics included frozen-route behavior
- this means the daemon process is up, but the mismatch/freeze problem is **not yet fully resolved**

## Highest-priority next actions
1. restart or re-run the daemon and observe whether the new post-submit snapshot sync removes periodic `SIZE_MISMATCH` freezes
2. inspect the persisted live-state / route-state artifacts after the next live cycle
3. inspect the exact exchange snapshot vs persisted local position for BTC trend account if `severe_alignment_issue` still appears
4. continue narrowing any remaining issue to:
   - stale persisted state carried forward
   - residual exchange-side position not represented locally before the cycle starts
   - route freeze state being restored correctly but not cleared when alignment recovers
5. only after mismatch is resolved, allow daemon to continue as trusted runtime

## Incremental update
- patched execution flow so local entry/exit state is no longer finalized from receipt size semantics
- pipeline now refreshes exchange snapshot after submit and explicitly copies latest exchange side/size into local state before verify/reconcile
- added regression coverage proving post-submit exchange contracts override mismatched receipt size during entry flow

## Important notes for next session
- direct Discord webhook path is working
- daemon direct notify is enabled
- daemon supervision is still just background process execution, not systemd-managed
- repo still has unrelated unstaged workspace changes/deletions/backups that were intentionally not included in the last pushes
