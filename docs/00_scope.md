# Scope

## Purpose

`trading-model` is the offline modeling home for the current eight-layer trading decision stack.

It owns point-in-time model research, model-local generators/evaluators, validation workflows, promotion evidence, model outputs, and decision-record prototypes for:

1. `MarketRegimeModel` -> `market_context_state`;
2. `SectorContextModel` -> `sector_context_state`;
3. `TargetStateVectorModel` -> `target_context_state`, with anonymous target candidate construction as Layer 3 preprocessing;
4. `EventOverlayModel` -> `event_context_vector`;
5. `AlphaConfidenceModel` -> `alpha_confidence_vector`;
6. `PositionProjectionModel` -> `position_projection_vector`;
7. `UnderlyingActionModel` -> `underlying_action_plan` / `underlying_action_vector`;
8. `OptionExpressionModel` -> `option_expression_plan` / `expression_vector`.

The repository does **not** place orders, mutate accounts, own provider acquisition, or become the global registry. It produces offline model artifacts and review evidence for downstream systems.

## In Scope

- Point-in-time model research, validation, promotion evidence, and reproducible local tests.
- Broad market tradability/regime state from market-only inputs.
- Market-context-conditioned sector/industry tradability state.
- Anonymous target candidate construction and target state-vector modeling without ticker/company identity in fitting vectors.
- Event-context modeling from visible point-in-time events before alpha confidence.
- Alpha-confidence modeling from reviewed state stack plus event correction.
- Position-projection modeling from adjusted alpha plus current/pending position, cost, exposure, and risk-budget context; this projects target position state, not orders.
- Underlying-action modeling for offline direct stock/ETF action thesis, planned exposure change, price-path assumptions, and Layer 8 handoff; this is not broker execution.
- Option-expression modeling from the Layer 7 thesis plus option-chain context; this may choose expression/contract constraints, not routes or orders.
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

The active route is current-route authoritative. Historical route changes belong in Git history, not in active docs or package names.

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
