# State and Artifacts

## State path

State is stored at:
- `/root/.openclaw/workspace/projects/crypto-trading/logs/state.json`

Tracked state includes:
- open positions keyed as `strategy:symbol`
- last signal per strategy/symbol bucket
- per-bucket capital (`initial_capital_usdt`, `available_usdt`, `allocated_usdt`)
- execution history

## Runtime artifacts

Primary runtime artifacts:
- `logs/runtime/latest-execution-cycle.json`
- `logs/runtime/execution-cycles.jsonl`

## Current artifact fields of interest

- `summary`
- `compare_snapshot`
- `receipt`
- `summary.account_metrics`

## Exit behavior

- If a bucket has an open position and its current strategy signal turns `flat`, the runner closes that tracked demo position.
- If a bucket has an open position and the strategy flips to the opposite side, the runner first closes the existing tracked position.
- In demo-submit mode, exit orders are sent as reduce-only market orders using the tracked contract amount from the entry.

## Current state

Artifacts are now part of the traceable review data path, not just debugging leftovers.
