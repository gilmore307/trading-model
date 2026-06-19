# Context

## Why This Repository Exists

The trading platform is split across multiple repositories so each major responsibility has a clear owner. `trading-model` exists as the offline modeling home for the direction-neutral trading decision system. The current model stack has six contracts:

1. BackgroundContextModel (`background_context_model`);
2. TargetStateModel (`target_state_model`);
3. EventStateModel (`event_state_model`);
4. UnifiedDecisionModel (`unified_decision_model`);
5. OptionExpressionModel (`option_expression_model`);
6. ResidualEventGovernanceModel (`residual_event_governance_model`).

M04, M05, and M06 plans remain offline and broker mutation stays outside this repository.

Current structural boundary:

```text
background context -> target state -> event state -> unified decision -> optional option expression -> residual event governance
```

`BackgroundContextModel` describes broad market and sector/industry background in one model. `TargetStateModel` builds anonymous target candidates and evaluates target state. `EventStateModel` applies accepted event-family and strategy-failure conditioning without changing event parameters. `UnifiedDecisionModel` produces the direct-underlying decision with structured edge, risk, exposure, and action heads. `OptionExpressionModel` composes optional offline trading guidance and option-expression context from that intent. `ResidualEventGovernanceModel` may intervene on the direct-underlying/spot thesis with point-in-time residual event risk while treating option-expression context as optional. Later decision/expression/governance layers may map back to real symbols only for audit, routing, and decision records.

Historical retired serial package names are not a parallel current standard.

## Related Systems

| System | Relationship |
|---|---|
| `trading-manager` | Owns global architecture, registry, templates, shared helpers, and cross-repository contracts. |
| `trading-manager` control plane | Owns orchestration, lifecycle, scheduling, retries, requests, and promotion routing. |
| `trading-data` | Produces point-in-time data/source-evidence artifacts consumed by model research. |
| `trading-storage` | Owns durable storage layout, retention, archive, backup, restore, and artifact placement rules. |
| `trading-strategy` | May provide downstream action/expression research artifacts if revived; active decision and expression translation live in `trading-model` until a separate owner is explicitly restored. |
| `trading-model` | Produces offline direction-neutral model research outputs, validation evidence, and decision-record prototypes. |
| `trading-execution` | Consumes promoted decisions/risk-approved orders for paper/live execution; broker mutation is not owned here. |
| `trading-dashboard` | Presents already-produced outputs and evidence. |

## Expected External Interfaces

Potential external interfaces include:

- `trading-data` artifacts and manifests for market data, option-chain snapshots, macro/event evidence, ETF holdings, and source availability.
- Strategy/action research outputs, model-local during current decision/expression development or from `trading-strategy` only if that repository is explicitly revived as owner.
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

- Python and standard library for local generators/tests;
- optional PostgreSQL access for read-only SQL evidence and reviewed model-output writes;
- `trading-manager` registry/shared environment conventions;
- `trading-storage` artifact roots for durable evidence.
