# Scope

## Purpose

`trading-model` is the offline modeling home for the current M01-M05 probability trading decision stack, plus compatibility event-governance evidence that feeds M03.

It owns point-in-time model research, model-local generators/evaluators, validation workflows, promotion evidence, model outputs, and decision-record prototypes for:

1. `BackgroundContextModel` -> `background_context_state`;
2. `TargetStateModel` -> `target_context_state`;
3. `EventStateModel` -> `event_state_vector`;
4. `UnifiedDecisionModel` -> `thesis_distribution_surface` plus derived `unified_decision_vector`;
5. `OptionExpressionModel` -> `expression_probability_surface` plus derived `option_expression_plan` / `expression_vector`.

The repository does **not** place orders, mutate accounts, own provider acquisition, or become the global registry. It produces offline model artifacts and review evidence for downstream systems.

## In Scope

- Point-in-time model research, validation, promotion evidence, and reproducible local tests.
- Broad market and sector/industry background state from point-in-time market, sector, liquidity, volatility, breadth, correlation, dispersion, and macro-sensitive inputs.
- Anonymous target candidate construction, target ranking, and target-state modeling without ticker/company identity in fitting vectors.
- Event-state modeling from accepted event-family and strategy-failure relationships without mutating event-family parameters.
- Unified direct-underlying decision modeling with structured edge, risk, exposure, and action heads.
- Option-expression modeling from unified direct-underlying intent plus optional option-chain context; this may choose offline expression/contract constraints, not routes or broker orders.
- Compatibility event-governance evidence, including missed-event checks, residual attribution, event-family modelability, and future event-family packet eligibility, only as evidence that feeds M03 taxonomy/effect-model contracts.
- Model-local labels, diagnostics, explainability, fixtures, and acceptance gates.
- Proposing shared names/contracts to `trading-manager` when model outputs need cross-repository consumption.

## Out of Scope

- Provider/API/web/file fetching, feed ownership, raw-source normalization, and data-source/data-feature production.
- Live/paper order placement, broker interaction, order routing, account mutation, fills, cancels, replaces, or lifecycle retries.
- Production scheduling, orchestration, and promotion lifecycle control unless delegated by an accepted contract.
- Dashboard rendering.
- Durable storage layout, retention, backup, or restore policy unless proposing a reviewed contract.
- Global contract/type/field/status registration outside `trading-manager`.
- Generated data, artifacts, logs, notebooks, credentials, or secrets committed to Git.

## Owner Intent

`trading-model` should be direct and disciplined: one folder per accepted model boundary, clear point-in-time inputs, narrow primary outputs, separate explainability/diagnostics, explicit labels, and evidence-backed acceptance.

The active route is current-route authoritative. Historical route changes belong in Git history, not in active docs, package names, or entrypoints.

## Boundary Rules

- Component-local modeling code belongs here when it matches the accepted offline modeling role.
- Data acquisition/source cleaning/data-feature generation belongs in `trading-data`.
- Global contracts, registry entries, shared helpers, reusable templates, and lifecycle policy belong in `trading-manager`.
- Durable storage layout and retention belong in `trading-storage` unless this repository is defining a proposed contract for review.
- Live execution and broker/account mutation stay outside this repository.
- Generated artifacts and runtime outputs are not source files.
- Secrets and credentials must stay outside the repository.
- New shared helpers, fields, statuses, artifacts, config keys, and type values must be registered through `trading-manager` before cross-repository use.

## Re-scope Signals

Re-scope or reject a request if it asks `trading-model` to:

- fetch or normalize raw provider data as an acquisition bundle;
- place, cancel, route, or modify live/paper trades;
- commit generated runtime outputs or secrets;
- define global contracts without registry review;
- bypass accepted storage or manager lifecycle boundaries;
- treat fixture/local evidence as production promotion.
