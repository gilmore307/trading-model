# Acceptance

## Acceptance Summary

`trading-model` is accepted when it provides a clear, testable component boundary for its role in the trading system.

Acceptance focuses on:

- repository boundary clarity;
- workflow clarity;
- compatibility with `trading-manager` contracts and registry rules;
- compatibility with `trading-storage` where durable artifacts are involved;
- absence of committed generated outputs, logs, notebooks, credentials, and secrets;
- evidence-backed tests once code exists.

## Acceptance Rules

### For Documentation Changes

Documentation changes are acceptable when they:

- update the narrowest authoritative file;
- preserve separation between scope, context, workflow, acceptance, task, decision, and memory;
- route global helper, template, field, status, type, and shared vocabulary changes to `trading-manager`;
- mark unresolved contract/storage/runtime questions as open gaps;
- avoid pretending implementation choices are settled before evidence exists.

### For Implementation Changes

Implementation changes are acceptable only when they:

- stay inside this repository's component boundary;
- avoid committing generated data, artifacts, logs, notebooks, credentials, or secrets;
- include meaningful tests for the behavior introduced;
- avoid external side effects in default tests unless explicitly guarded;
- use accepted contracts for cross-repository handoffs;
- route new shared names through `trading-manager/scripts/`.

## Verification Commands

Current implementation checks:

```bash
python3 -m compileall -q src scripts tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/generate_model_01_market_regime.py --help
PYTHONPATH=src python3 scripts/ensure_model_governance_schema.py --help
PYTHONPATH=src python3 scripts/ensure_model_governance_schema.py
PYTHONPATH=src python3 scripts/evaluate_model_01_market_regime.py --help
PYTHONPATH=src python3 scripts/evaluate_model_01_market_regime.py
git diff --check
```

Runtime SQL smoke tests require an explicitly configured PostgreSQL target and should not run as default unit tests.

## Required Review Evidence

Every accepted change should provide:

- changed files;
- boundary impact;
- contract impact;
- registry impact;
- storage impact;
- test/verification output;
- confirmation that no generated outputs, logs, notebooks, credentials, or secrets were committed;
- unresolved gaps routed to `docs/04_task.md`.

## Rejection Reasons

A change must be rejected or returned if it:

- takes over another component repository responsibility.
- commits generated outputs, logs, notebooks, or credentials.
- invents shared fields/statuses/types without trading-manager registry review.
- stores secret values.
- writes artifacts to undocumented paths.
- claims acceptance without test or inspection evidence.
- duplicates global contract definitions locally instead of referencing trading-manager.
