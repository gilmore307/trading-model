# Context

## Why This Repository Exists

The trading platform is split across multiple repositories so each major responsibility has a clear owner. `trading-model` exists as the offline modeling home for the direction-neutral trading decision system:

1. MarketRegimeModel (`market_regime_model`);
2. SectorContextModel (`sector_context_model`);
3. TargetStateVectorModel (`target_state_vector_model`), including anonymous target candidate construction as Layer 3 preprocessing;
4. AlphaConfidenceModel (`alpha_confidence_model`);
5. TradingProjectionModel (`trading_projection_model`);
6. OptionExpressionModel (`option_expression_model`);
7. PortfolioRiskModel (`portfolio_risk_model`).

Event evidence remains an overlay/input to target-state, confidence, projection, expression, and risk work rather than a peer to the three core tradability layers.

The repository turns point-in-time data artifacts and strategy/event evidence into model research, validation results, decision-record prototypes, and model outputs. It does not own raw source acquisition or live execution.

Current structural boundary:

```text
broad market tradability context -> sector/industry tradability context -> anonymized target tradability state vector -> confidence -> trading projection
```

`MarketRegimeModel` describes the broad environment. `SectorContextModel` studies direction-neutral sector/industry tradability under each broad market state. Layer 3 preprocessing builds anonymous target candidates, then `TargetStateVectorModel` evaluates anonymized target candidates with market and sector context. Later confidence/projection/expression/risk layers may map back to real symbols only for audit, routing, and decision records.

## Related Systems

| System | Relationship |
|---|---|
| `trading-manager` | Owns global architecture, registry, templates, shared helpers, and cross-repository contracts. |
| `trading-manager` control plane | Owns orchestration, lifecycle, scheduling, retries, requests, and promotion routing. |
| `trading-data` | Produces point-in-time data/source-evidence artifacts consumed by model research. |
| `trading-storage` | Owns durable storage layout, retention, archive, backup, restore, and artifact placement rules. |
| `trading-strategy` | May provide downstream action/expression research artifacts if kept separate; Layer 3 remains target-state construction, not action selection. |
| `trading-model` | Produces offline direction-neutral model research outputs, validation evidence, and decision-record prototypes. |
| `trading-execution` | Consumes promoted decisions/risk-approved orders for paper/live execution; broker mutation is not owned here. |
| `trading-dashboard` | Presents already-produced outputs and evidence. |

## Expected External Interfaces

Potential external interfaces include:

- `trading-data` artifacts and manifests for market data, option-chain snapshots, macro/event evidence, ETF holdings, and source availability.
- Strategy definitions/backtest outputs, either model-local during research or from `trading-strategy` if that repository remains the strategy owner.
- Event evidence and event-cluster artifacts once accepted.
- Storage artifact references from `trading-storage`.
- Shared registry fields/contracts from `trading-manager`.

Specific providers, credentials, package choices, deployment targets, and runtime settings are not settled unless recorded in this repository's decisions or inherited from `trading-manager` contracts.

## Point-in-Time Constraint

Every model must obey:

```text
At time t, the model may only use data genuinely available before or at t.
```

Model-facing data and labels should distinguish when relevant:

- `event_time` — when something happened or was scheduled to happen;
- `available_time` — when evidence became visible to the system;
- `tradeable_time` — when the system could realistically trade on it.

Using post-event explanations or full-history transformations to train/predict earlier timestamps is a rejection reason.

## Environment

Development is server-hosted under `/root/projects/trading-model`.

The shared Python environment is anchored by `trading-manager` at:

```text
/root/projects/trading-manager/.venv
```

`trading-model` should not create an independent virtual environment unless a documented exception is accepted.

## Dependencies

Current system-level dependencies:

- `trading-manager/docs/90_helpers.md` for shared helper policy;
- `trading-manager/docs/91_registry.md` for registry operating rules;
- `trading-manager/docs/92_templates.md` and `trading-manager/templates/` for reusable drafting surfaces;
- `trading-manager/requirements.txt` for reviewed shared Python dependencies;
- related component repositories through accepted contracts, not internal implementation details.

## Global Registration Discipline

If this repository introduces a name that other repositories may consume, route it back to `trading-manager` before treating it as stable.

This includes shared fields, artifact types, manifest types, ready-signal types, request types, status values, global helper methods, reusable templates, config keys, and provider-independent terminology.

## Important Constraints

- Do not store generated artifacts, logs, notebooks, credentials, or secrets in Git.
- Keep component-local implementation inside this repository's offline modeling boundary.
- Use manifests, ready signals, artifact references, and requests for cross-repository handoffs once contracts are accepted.
- Do not depend on another component's internal implementation details.
