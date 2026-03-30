# Research Pipeline Automation

_Date: 2026-03-27_

## Goal

Run the BTC research pipeline continuously without spending tokens on routine fetch/build/evaluate work.

Design rule:
- scripts and schedulers do the repetitive work
- rule-based checks flag anomalies
- an agent only joins when results need interpretation, prioritization, or debugging

## Current automation scope

The current orchestrated pipeline covers:

1. fetch OKX 1m candles
2. fetch Bitget derivatives context
3. build `crypto_market_state_dataset_v1`
4. build `ma_parameter_utility_dataset_v1`
5. build `donchian_parameter_utility_dataset_v1`
6. build `bollinger_parameter_utility_dataset_v1`
7. combine family datasets into `strategy_parameter_utility_dataset_v1`
8. build state × family × parameter-region report
9. build unsupervised clustering baseline
10. persist timestamp-level labels
11. evaluate labels against MA parameter-region utility
12. refresh market-discovery payload

## Main entrypoints

### Run the full pipeline

```bash
./scripts/pipeline/run_research_pipeline.sh
```

### Run only selected steps

```bash
./scripts/pipeline/run_research_pipeline.sh --only-step build_market_state_dataset --only-step build_ma_utility_dataset
```

### Skip selected steps

```bash
./scripts/pipeline/run_research_pipeline.sh --skip-step fetch_okx_candles
```

### Run anomaly checks

```bash
./scripts/pipeline/check_research_anomalies.sh
```

## State and logs

Pipeline state lives under:

- `logs/pipeline/runs/<run_id>/manifest.json`
- `logs/pipeline/runs/<run_id>/<step>.log`
- `logs/pipeline/state/latest_run.json`
- `logs/pipeline/state/latest_anomalies.json`

## Agent participation policy

### No agent needed

Use scripts/scheduler only for:
- data fetch
- resume/backfill
- dataset builds
- batch evaluation
- timestamp-label generation
- fixed export generation
- rule-based anomaly checks

### Agent needed

Use an agent only for:
- repeated failures or broken data-source behavior
- interpreting surprising shifts in cluster structure
- deciding next research direction
- writing condensed conclusions / docs
- designing the next experiment set

## Suggested scheduler split

### High-frequency machine-only tasks

- fetch data every 15-60 minutes
- rebuild derived datasets after fresh data lands
- refresh labels/evaluation on a slower cadence if compute is heavy
- rely on orchestrator freshness skipping so heavy downstream steps are not recomputed when inputs are unchanged

### Lower-frequency review tasks

- anomaly checks every run or every few runs
- agent review only when anomaly output is non-empty or a major result changes

## Incremental behavior

The orchestrator now supports a first-pass freshness check:

- steps may declare `inputs` and `outputs` in `config/research_pipeline.json`
- if all declared outputs exist and are newer than the declared inputs, the step is skipped
- fetch steps are still allowed to run normally because they are the source of new data

This is not yet a full content-hash build system, but it already avoids rerunning the heaviest downstream steps when upstream data has not changed.

## Scheduler units

Systemd unit templates now live under:

- `deploy/systemd/crypto-trading-research-pipeline.service`
- `deploy/systemd/crypto-trading-research-pipeline.timer`
- `deploy/systemd/crypto-trading-research-anomaly-check.service`
- `deploy/systemd/INSTALL.md`

## Current limitations

- the incremental logic is mtime-based, not hash/content-based
- the MA utility dataset still rebuilds from current inputs rather than using a richer cached multi-family workflow
- only the MA family is wired into this automated pipeline today
- agent escalation is still a policy boundary, not yet an automatic downstream trigger

## Next buildout priorities

1. add multi-family utility dataset generation
2. make step-level dependency checks more incremental
3. add scheduler units/timers
4. add machine-readable result comparison across runs
5. add agent summary hook only for anomaly/escalation cases
