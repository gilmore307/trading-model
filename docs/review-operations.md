# Review Operations

This document is the operator/runbook entry for the review pipeline.

## Current scope

The project now has a first usable review artifact pipeline with:

- canonical performance ingestion from execution artifacts
- execution-history aggregation
- weekly/monthly/quarterly review report generation
- JSON + Markdown export under `reports/trade-review/`

## Primary artifact source

Execution history is read from:

- `logs/runtime/execution-cycles.jsonl`

Review reports are written to:

- `reports/trade-review/`

Convenience files maintained automatically:

- `latest_weekly.json` / `latest_weekly.md`
- `latest_monthly.json` / `latest_monthly.md`
- `latest_quarterly.json` / `latest_quarterly.md`
- `index.json` — rolling report index with latest-by-cadence pointers

## Weekly review

Generate a weekly review anchored to a UTC timestamp:

```bash
./.venv/bin/python scripts_weekly_review.py --now 2026-03-15T12:00:00+00:00
```

Optional flags:

```bash
./.venv/bin/python scripts_weekly_review.py \
  --now 2026-03-15T12:00:00+00:00 \
  --history-path /root/.openclaw/workspace/projects/crypto-trading/logs/runtime/execution-cycles.jsonl \
  --out-dir /root/.openclaw/workspace/projects/crypto-trading/reports/trade-review
```

Window rule:

- weekly review currently closes at UTC Saturday 00:00
- output label format: `weekly:START->END`

## Monthly review

Generate a monthly review anchored to a UTC timestamp:

```bash
./.venv/bin/python scripts_monthly_review.py --now 2026-03-15T12:00:00+00:00
```

Optional explicit previous boundary:

```bash
./.venv/bin/python scripts_monthly_review.py \
  --now 2026-03-15T12:00:00+00:00 \
  --previous-review-end 2026-02-01T00:00:00+00:00
```

Window rule:

- monthly review currently covers start-of-previous-UTC-month -> start-of-current-UTC-month
- output label format: `monthly:START->END`

## Quarterly review

Generate a quarterly review anchored to a UTC timestamp:

```bash
./.venv/bin/python scripts_quarterly_review.py --now 2026-05-15T12:00:00+00:00
```

Optional explicit previous boundary:

```bash
./.venv/bin/python scripts_quarterly_review.py \
  --now 2026-05-15T12:00:00+00:00 \
  --previous-review-end 2026-01-01T00:00:00+00:00
```

Window rule:

- quarterly review currently covers start-of-previous-UTC-quarter -> start-of-current-UTC-quarter
- output label format: `quarterly:START->END`

## Output contents

Each review export produces:

- one JSON artifact
- one Markdown artifact

The report currently contains:

- executive summary
- recommended actions
- account comparison section
- router composite review section
- parameter review section
- section status summary

## Operational intent

The review path is being built so that the trading core stays portable while OpenClaw remains an orchestration/operator layer.

That means:

- the report generation itself should remain callable as normal Python runners
- OpenClaw cron / session orchestration may trigger it
- future non-OpenClaw schedulers should be able to call the same runner scripts unchanged

## Related documents

- `docs/review-automation.md` — scheduling / deployment / OpenClaw-vs-non-OpenClaw automation notes

## Near-term next steps

- improve canonical realized/unrealized/funding semantics
- add report index / latest-pointer convenience files
- document exact OpenClaw cron job examples when scheduling is turned on
