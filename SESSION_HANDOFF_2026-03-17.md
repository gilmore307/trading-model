# SESSION_HANDOFF_2026-03-17

_Last updated: 2026-03-17 01:57 Asia/Shanghai_

## Session summary

This session resumed the crypto-trading runtime recovery line. The main outcomes were:
- crowded API credentials updated locally
- daemon / notifier path investigated and improved
- direct Discord webhook notifications wired into the daemon and validated
- reconciliation logic hardened around size semantics, post-submit snapshot refresh, and local state persistence
- daemon restarted successfully, but the runtime still hit `severe_alignment_issue` immediately on a live BTC trend cycle

## Key findings

### Process / runtime operations
- trade daemon was not running at session start
- historical runs looked like unsupervised background shell processes rather than managed service runs
- absence of `daemon_stopped` and `cycle_error` in earlier long runs suggested abrupt external termination or session loss

### Direct notifications
- watcher-based polling path was considered too API-heavy
- daemon-direct notification path is now the intended direction
- webhook connectivity was confirmed with a standalone test message

### Reconciliation diagnosis
Most important suspected causes identified this session:
1. local position size semantics vs exchange contracts semantics diverged
2. verify/reconcile had been using pre-submit snapshots
3. local route/live state had been process-memory only and reset on restart

## Code landed this session
- `3de2713` — direct Discord notifications from daemon
- `8c84ed1` — runtime reconciliation hardening + persistence tests

## What changed technically
- local entry tracking now prefers execution receipt size when available
- exchange snapshot is refreshed after submit before verify/reconcile
- live position store persists to runtime JSON
- route registry persists to runtime JSON
- tests updated to isolate persisted state and cover new persistence behavior

## Runtime state at handoff
Daemon status during session closeout:
- daemon was started successfully in background
- first live post-restart cycle still showed:
  - `BTC-USDT-SWAP`
  - `trend`
  - `hold`
  - `block_reason = severe_alignment_issue`

Interpretation:
- process startup path is working
- direct notify path is working
- a real mismatch / freeze condition still exists in live state
- this is no longer just a daemon-launch problem

## Next recommended actions
1. inspect persisted runtime files under `logs/runtime/`:
   - live-state-store
   - route-registry
   - latest execution artifact
2. compare persisted local trend BTC position against exchange live snapshot
3. determine whether the remaining mismatch is due to:
   - residual exchange position
   - persisted stale local state
   - adapter receipt size not matching actual exchange contracts in some path
   - route re-enable path not firing after alignment recovery
4. once mismatch root cause is confirmed, either clear bad state safely or patch the remaining semantic gap

## Notes
- direct webhook is configured locally in project `.env`
- unrelated repo deletions/backups remain outside the last pushed commits by design
