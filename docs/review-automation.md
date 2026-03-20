# Review Automation and Deployment Notes

This document describes how to schedule review generation now, while preserving a path to run the project outside OpenClaw later.

## Principle

Keep the trading/review core callable as normal Python entrypoints.

Use OpenClaw today as:

- orchestration layer
- operator interface
- optional scheduler / notifier

Avoid making report generation itself depend on OpenClaw-only internals.

## Review entrypoints

Current runner scripts:

- `scripts/scripts_weekly_review.py`
- `scripts/scripts_monthly_review.py`
- `scripts/scripts_quarterly_review.py`

Each script can be called directly with `.venv/bin/python` and supports `--history-path` / `--out-dir`.

## Current artifact source

Default review source:

- `logs/runtime/execution-cycles.jsonl`

Default output directory:

- `reports/trade-review/`

Convenience outputs now maintained automatically:

- cadence-specific latest pointers (`latest_weekly.*`, `latest_monthly.*`, `latest_quarterly.*`)
- `index.json` with rolling history and latest-by-cadence lookup

## OpenClaw-first automation path

Recommended near-term pattern:

1. keep execution/runtime artifact generation inside the existing project runtime
2. schedule weekly/monthly/quarterly review runs via OpenClaw cron or operator-triggered sessions
3. optionally send the resulting Markdown artifact to Discord or another channel after generation

Why this path is good now:

- minimum extra deployment work
- keeps operator workflow centralized
- preserves future portability because the scheduled task calls normal Python scripts

## Non-OpenClaw scheduler path

If later moving away from OpenClaw orchestration, the same scripts can be scheduled with:

- `cron`
- `systemd timers`
- `supervisord` or another job runner
- CI/CD scheduled workflows (if artifacts live on an attached host)

Example weekly cron:

```cron
5 0 * * 6 cd /root/.openclaw/workspace/projects/crypto-trading && ./.venv/bin/python scripts/scripts_weekly_review.py >> logs/weekly-review.log 2>&1
```

Example monthly cron:

```cron
10 0 1 * * cd /root/.openclaw/workspace/projects/crypto-trading && ./.venv/bin/python scripts/scripts_monthly_review.py >> logs/monthly-review.log 2>&1
```

Example quarterly cron:

```cron
15 0 1 1,4,7,10 * cd /root/.openclaw/workspace/projects/crypto-trading && ./.venv/bin/python scripts/scripts_quarterly_review.py >> logs/quarterly-review.log 2>&1
```

## Suggested operator workflow

### Weekly

- check runtime health / artifacts
- run weekly review
- inspect Markdown report first
- decide whether any `candidate` or `discuss_first` parameter items should enter the calibration process

### Monthly

- run monthly review
- focus on multi-week account stability and router behavior
- use monthly output as the main discussion layer for parameter changes that should not auto-apply casually

### Quarterly

- run quarterly review
- focus on structural review, taxonomy, risk framework, and long-horizon account/strategy fitness

## Meta-work expectations

For this project, review automation is not complete unless it has:

- a callable runner
- tests
- output location conventions
- docs/runbook coverage
- a migration path for non-OpenClaw scheduling

## Near-term next steps

- optionally add a post-run notifier wrapper
- document exact OpenClaw cron job examples when scheduling is turned on
- continue improving canonical performance semantics before any automatic parameter adoption
