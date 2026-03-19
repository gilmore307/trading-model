# Parameter Promotion Workflow

_Last updated: 2026-03-20_

## Goal

When historical replay / research finds a better parameter set, the live runtime should be able to adopt it **immediately and safely**.

Key principle:

- historical validation and live trading share the **same decision logic**
- they differ only in execution backend
- parameter changes discovered offline should move into live runtime through a **publish / activate / rollback** mechanism
- parameter updates must not rely on ad-hoc manual edits scattered across `.env` or code defaults

## Core principle

### Same strategy logic, different execution backend

Historical validation should reuse:
- regime classifier
- router
- executor logic
- scores / blockers / subscores
- parameter meanings

Historical validation should replace only:
- exchange account backend
- order submission
- live reconciliation

with:
- simulated execution backend
- paper ledger
- historical fill/fee/slippage model

## Parameter lifecycle

### 1. Baseline parameters
Source of truth today:
- `src/config/settings.py`
- environment variables from `.env`

Role:
- fallback defaults
- startup-safe values
- emergency rollback target

### 2. Research candidate parameters
Produced by:
- historical replay / review / parameter search

Stored as versioned artifacts, for example under:
- `artifacts/parameters/candidates/`

Each candidate artifact should contain:
- candidate id
- generated_at
- source mode (`historical_replay` / `snapshot_backtest` / later others)
- source period/window
- review cadence (`weekly` / `monthly` / `quarterly`)
- symbol scope
- regime scope
- strategy scope
- baseline objective summary
- candidate objective summary
- parameter diff
- full parameter set
- notes / recommendation

### 3. Active live parameters
Stored separately from research candidates, for example:
- `config/active-parameters.json`

Role:
- single live runtime source of truth for promoted parameter overrides
- loaded by daemon at startup
- optionally hot-reloaded later, but startup-load is the minimum requirement

### 4. Previous live parameters
Stored as rollback history, for example:
- `config/parameter-history/<version>.json`

Role:
- safe rollback target
- audit trail of parameter promotions

## Required workflow

### Step A: historical replay / research generates candidate
Historical system runs:
- same decision logic
- simulated execution
- weekly/monthly/quarterly style review

Output includes:
- candidate parameter artifact
- evidence summary
- comparison against currently active baseline

### Step B: candidate review
Operator checks:
- source period and sample size
- whether improvement is robust or noisy
- whether the candidate is regime-specific or global
- whether the objective improvement is worth promoting

### Step C: publish / activate
Promotion writes candidate into live-active storage:
- update `config/active-parameters.json`
- archive previous active version
- record activation metadata

### Step D: live runtime picks up active parameters
Minimum version:
- daemon reads active parameter overrides at startup

Preferred later version:
- daemon can reload parameters without restart
- but only if safety and consistency are preserved

### Step E: rollback if needed
If live behavior degrades:
- revert to previous active version quickly
- restart or reload daemon
- preserve rollback event in parameter history

## Proposed artifact shape

### Candidate artifact example

```json
{
  "candidate_id": "cand_20260320T024500Z_trend_weekly_001",
  "generated_at": "2026-03-20T02:45:00Z",
  "source": {
    "mode": "historical_replay",
    "review_cadence": "weekly",
    "period_start": "2025-12-01T00:00:00Z",
    "period_end": "2025-12-08T00:00:00Z",
    "symbol": "BTC-USDT-SWAP",
    "regime": "trend",
    "strategy": "trend"
  },
  "baseline": {
    "parameter_version": "live_20260318T120000Z",
    "objective_score": 8.4
  },
  "candidate": {
    "objective_score": 9.1,
    "parameter_overrides": {
      "trend_bg_adx_min": 28.0,
      "trend_primary_adx_min": 26.0,
      "trend_follow_through_enter_min": 4.0
    }
  },
  "recommendation": {
    "action": "promote_for_live",
    "confidence": "medium",
    "notes": [
      "weekly replay improved avg_enter_forward_return",
      "enter frequency decreased but objective improved"
    ]
  }
}
```

### Active live parameter file example

```json
{
  "version": "live_20260320T024800Z",
  "activated_at": "2026-03-20T02:48:00Z",
  "source_candidate_id": "cand_20260320T024500Z_trend_weekly_001",
  "overrides": {
    "trend_bg_adx_min": 28.0,
    "trend_primary_adx_min": 26.0,
    "trend_follow_through_enter_min": 4.0
  }
}
```

## Loading model for runtime

### Minimum implementation
At startup, `Settings.load()` should:
1. load `.env` defaults
2. load active parameter override file if present
3. apply only whitelisted tunable keys
4. continue running if file is absent or invalid, but log a warning

### Safety rules
- only whitelisted parameter keys may be overridden
- credentials, account aliases, and execution-mode flags must not be overridden by research candidates
- invalid active parameter file must fail closed to baseline defaults
- promotion must never silently modify API credentials or account routing

## Separation between research and runtime

### Allowed shared items
- parameter names
- decision logic
- executor logic
- review cadence semantics

### Must remain separate
- historical candidate generation
- live activation state
- exchange credentials
- order submission side effects
- reconciliation state

Research may suggest parameters.
Runtime decides only whether to load the already-published active set.

## Immediate implementation plan

### P1
1. define a whitelist of tunable parameter keys
2. add active parameter override loading to `Settings.load()`
3. add a candidate artifact writer for historical replay results
4. add a small promotion script:
   - candidate -> active
   - archive previous active version

### P2
5. add rollback script
6. add startup log fields showing active parameter version
7. include active parameter version in execution artifacts and reviews

### P3
8. optionally add hot reload
9. optionally add promotion guards based on minimum sample / confidence

## Completion standard

This workflow is materially complete when:
1. historical replay can emit candidate parameter artifacts
2. live runtime can load active parameter overrides from a single source of truth
3. activation and rollback are both explicit and reversible
4. runtime and historical validation still use the same decision logic
