# Parameter Change Log Spec

## Purpose

This file defines the event-log format used by dashboard surfaces such as Market Discovery.

The key rule is:

- record **change events**, not only current parameter snapshots

That preserves:

- who changed something
- why it changed
- what state/cluster it was tied to
- whether it was only proposed, reviewed, activated, or later superseded/reverted

## Current storage

Current file:

- `data/derived/parameter_change_log.json`

## Schema

```json
{
  "generatedAt": "2026-03-27T15:15:00+08:00",
  "schemaVersion": "parameter_change_log_v1",
  "events": [
    {
      "timestamp": "2026-03-25T14:00:00Z",
      "symbol": "BTC-USDT-SWAP",
      "cluster_id": 0,
      "state_label": "High Volume Drift Up",
      "family": "ma_cross",
      "parameter_key": "threshold_enter_pct",
      "old_value": 0.0015,
      "new_value": 0.002,
      "parameter_region_before": "fast_windows__mid_threshold",
      "parameter_region_after": "fast_windows__wide_threshold",
      "change_type": "candidate",
      "reason": "Cluster 0 下 wide threshold 平均 utility 更高。",
      "source": "research",
      "operator": "Forge",
      "version": "cand_20260325_1400",
      "status": "proposed"
    }
  ]
}
```

## Field notes

- `timestamp` — when the event was recorded
- `symbol` — market scope
- `cluster_id` / `state_label` — optional state context for why the change was made
- `family` — strategy family scope
- `parameter_key` — changed field
- `old_value` / `new_value` — explicit before/after values
- `parameter_region_before` / `parameter_region_after` — higher-level region migration when relevant
- `change_type` — workflow stage (`candidate`, `reviewed`, `activated`, `rolled_back`, `manual_edit`)
- `reason` — human-readable explanation
- `source` — where the proposal/action came from (`research`, `review`, `manual`, `runtime`)
- `operator` — actor who recorded or applied the change
- `version` — candidate/review/live version label
- `status` — lifecycle state (`proposed`, `active`, `superseded`, `reverted`, `deprecated`)

## Dashboard contract

Dashboard consumers should read this file as an append-oriented event log.

They should not assume:

- only one row per parameter
- only one row per cluster
- only active rows matter

The UI may filter or summarize, but the storage layer should keep full event history.

## Maintenance workflow

Preferred append path:

```bash
python3 src/runners/append_parameter_change_event.py \
  --symbol BTC-USDT-SWAP \
  --cluster-id 4 \
  --state-label "High Vol Breakout Up" \
  --family ma_cross \
  --parameter-key threshold_enter_pct \
  --old-value 0.002 \
  --new-value 0.0012 \
  --parameter-region-before fast_windows__wide_threshold \
  --parameter-region-after fast_windows__tight_threshold \
  --change-type reviewed \
  --reason "High-vol breakout state favors tighter entry threshold." \
  --source review \
  --operator Forge \
  --version rev_20260325_1800 \
  --status active
```

Use the append script instead of hand-editing JSON whenever practical.
