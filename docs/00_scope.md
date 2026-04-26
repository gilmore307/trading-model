# Scope

## Purpose

`trading-model` is the offline modeling and market-state research repository for the trading system.

It discovers market states from market-only features, evaluates state usefulness after attaching strategy results, and produces mappings, confidence, research verdicts, manifests, and ready signals.

This repository exists to keep that responsibility explicit, testable, and separate from neighboring trading repositories.

## In Scope

- market-state discovery from market/data-source features.
- offline model research and evaluation workflows.
- state tables, mappings, confidence outputs, and research verdicts.
- post-discovery attachment of strategy results for evaluation.
- model-local tests and reproducibility evidence.

## Out of Scope

- market data fetching or normalization.
- strategy implementation or backtest execution.
- live/paper execution.
- dashboard rendering.
- shared storage policy.
- global contract/type registration outside trading-main.
- Defining global artifact, manifest, ready-signal, request, field, status, or type contracts outside `trading-main`.
- Storing generated data, artifacts, logs, notebooks, credentials, or secrets in Git.

## Owner Intent

`trading-model` should become a disciplined component repository with clear contracts, evidence-backed acceptance, and no hidden ownership drift.

The repository should prefer explicit interfaces, fixture-backed tests, and narrow responsibility boundaries over quick scripts that blur component roles.

## Boundary Rules

- Component-local implementation belongs here only when it matches this repository's role.
- Global contracts, registry entries, shared helpers, and reusable templates belong in `trading-main`.
- Durable storage layout and retention belong in `trading-storage` unless this repository is defining that storage contract.
- Scheduling, retries, lifecycle routing, and promotion decisions belong in `trading-manager` unless explicitly delegated by contract.
- Generated artifacts and runtime outputs are not source files.
- Secrets and credentials must stay outside the repository.
- Shared helpers, templates, fields, statuses, and type values discovered here must be recorded through `trading-main` before cross-repository use.

## Out-of-Scope Signals

A request should be rejected or re-scoped if it asks `trading-model` to:

- take over another component repository responsibility.
- commit generated runtime outputs or secrets.
- define global contracts without routing them through trading-main.
- invent shared fields/statuses/types without registry review.
- bypass accepted storage or manager lifecycle boundaries.
