# Scope

## Purpose

`trading-model` is the offline modeling repository for the six-layer trading decision system.

It owns point-in-time model research, training/evaluation workflows, model-local feature/label logic, model verdicts, and reproducibility evidence for:

1. market state / regime modeling;
2. dynamic strategy selection research;
3. signal quality and trade-outcome prediction;
4. option contract / expression selection research;
5. event shock and abnormal-activity overlay modeling;
6. portfolio risk, sizing, and execution-gate modeling.

The repository does **not** place live orders. It produces offline research artifacts, model outputs, decision-record prototypes, validation evidence, and contract proposals for downstream systems.

## In Scope

- Point-in-time model research and validation workflows.
- Market-state/regime discovery from market-only features.
- Regime-conditioned strategy family/variant selection research.
- Signal-quality, meta-labeling, target/stop, MFE/MAE, and holding-period models.
- Option expression selection research using option-chain snapshots, liquidity, IV, Greeks, and conservative fill assumptions.
- Event overlay research for scheduled events, breaking news shocks, pre-event abnormal activity, and historical event-impact memory.
- Portfolio risk, sizing, exposure, execution-gate, exit-rule, and kill-switch research logic.
- Unified candidate-trade decision-record prototypes for audit, attribution, replay, and retraining.
- Model-local tests, fixtures, reproducibility evidence, and acceptance gates.
- Proposing shared names/contracts to `trading-main` when model outputs need cross-repository consumption.

## Out of Scope

- Market/source data fetching or raw-source normalization.
- Owning source-evidence bundles; those belong in `trading-data`.
- Live/paper order placement, broker interaction, or account mutation.
- Production scheduling, lifecycle routing, retries, or promotion orchestration.
- Dashboard rendering.
- Durable storage retention policy unless delegated by accepted contract.
- Global contract/type/field/status registration outside `trading-main`.
- Storing generated data, artifacts, logs, notebooks, credentials, or secrets in Git.

## Owner Intent

`trading-model` should become the disciplined offline modeling home for the full trading decision stack, not merely a market-state repository.

The repository should prefer explicit point-in-time interfaces, fixture-backed tests, walk-forward validation, and evidence-backed acceptance over quick scripts or hindsight analysis.

## Boundary Rules

- Component-local modeling code belongs here when it matches the six-layer offline modeling role.
- Raw acquisition and source-specific cleaning belong in `trading-data`.
- Global contracts, registry entries, shared helpers, and reusable templates belong in `trading-main`.
- Durable storage layout and retention belong in `trading-storage` unless this repository is defining a proposed contract for review.
- Scheduling, retries, lifecycle routing, and promotion decisions belong in `trading-manager` unless explicitly delegated by contract.
- Live execution and broker/account mutation stay outside this repository.
- Generated artifacts and runtime outputs are not source files.
- Secrets and credentials must stay outside the repository.
- Shared helpers, templates, fields, statuses, and type values discovered here must be recorded through `trading-main` before cross-repository use.

## Out-of-Scope Signals

A request should be rejected or re-scoped if it asks `trading-model` to:

- fetch or normalize raw provider data as an acquisition bundle;
- place, cancel, or modify live/paper trades;
- commit generated runtime outputs or secrets;
- define global contracts without routing them through `trading-main`;
- invent shared fields/statuses/types without registry review;
- bypass accepted storage or manager lifecycle boundaries.
