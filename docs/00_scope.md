# Scope

## Purpose

`trading-model` is the offline modeling repository for the direction-neutral trading decision system.

It owns point-in-time model research, training/evaluation workflows, model-local feature/label logic, model verdicts, and reproducibility evidence for:

1. MarketRegimeModel (`market_regime_model`);
2. SectorContextModel (`sector_context_model`);
3. TargetStateVectorModel (`target_state_vector_model`), including anonymous target candidate construction as Layer 3 preprocessing;
4. AlphaConfidenceModel (`alpha_confidence_model`);
5. TradingProjectionModel (`trading_projection_model`);
6. OptionExpressionModel (`option_expression_model`);
7. PortfolioRiskModel (`portfolio_risk_model`).

Event evidence remains in scope as an overlay/input to target-state, confidence, projection, expression, and risk work rather than a peer to the three core tradability layers.

The repository does **not** place live orders. It produces offline research artifacts, model outputs, decision-record prototypes, validation evidence, and contract proposals for downstream systems.

## In Scope

- Point-in-time model research and validation workflows.
- Market-state/regime discovery from market-only features.
- Market-state-conditioned sector/industry trend-stability modeling: identifying which sector/industry baskets are easiest to trade under each broad market environment, using sector/industry rotation, liquidity, optionability, and event exclusions. Holdings/exposure evidence is downstream candidate-builder input after Layer 2 selects/prioritizes sector baskets.
- Anonymous target-candidate and target state-vector research that combines broad market, sector/industry, and target-local state without memorizing ticker identity.
- Alpha/confidence research that maps target-state vectors to long/short direction confidence, expected value, risk, and uncertainty.
- Trading-projection research that maps confidence plus position/cost/risk context to offline target actions and target exposure.
- Option expression selection research using option-chain snapshots, market-state background, liquidity, IV, Greeks, and conservative fill assumptions.
- Event evidence research for scheduled events, breaking news shocks, pre-event abnormal activity, and historical event-impact memory as overlays/inputs to model layers.
- Portfolio risk, sizing, exposure, execution-gate, execution-style, exit-rule, and kill-switch research logic using market-state background plus portfolio reality.
- Unified candidate-trade decision-record prototypes for audit, attribution, replay, and retraining.
- Model-local tests, fixtures, reproducibility evidence, and acceptance gates.
- Proposing shared names/contracts to `trading-manager` when model outputs need cross-repository consumption.

## Out of Scope

- Market/source data fetching or raw-source normalization.
- Owning source-evidence bundles; those belong in `trading-data`.
- Live/paper order placement, broker interaction, or account mutation.
- Production scheduling, lifecycle routing, retries, or promotion orchestration.
- Dashboard rendering.
- Durable storage retention policy unless delegated by accepted contract.
- Global contract/type/field/status registration outside `trading-manager`.
- Storing generated data, artifacts, logs, notebooks, credentials, or secrets in Git.

## Owner Intent

`trading-model` should become the disciplined offline modeling home for the full trading decision stack, not merely a market-state repository.

The repository should prefer explicit point-in-time interfaces, fixture-backed tests, walk-forward validation, and evidence-backed acceptance over quick scripts or hindsight analysis. Its model structure separates broad market background, sector/industry background, and target-state anonymous target work.

## Boundary Rules

- Component-local modeling code belongs here when it matches the accepted offline modeling role and V2.2 direction-neutral tradability boundaries.
- Raw acquisition and source-specific cleaning belong in `trading-data`.
- Global contracts, registry entries, shared helpers, and reusable templates belong in `trading-manager`.
- Durable storage layout and retention belong in `trading-storage` unless this repository is defining a proposed contract for review.
- Scheduling, retries, lifecycle routing, and promotion decisions belong in the `trading-manager` control plane unless explicitly delegated by contract.
- Live execution and broker/account mutation stay outside this repository.
- Generated artifacts and runtime outputs are not source files.
- Secrets and credentials must stay outside the repository.
- Shared helpers, templates, fields, statuses, and type values discovered here must be recorded through `trading-manager` before cross-repository use.

## Out-of-Scope Signals

A request should be rejected or re-scoped if it asks `trading-model` to:

- fetch or normalize raw provider data as an acquisition bundle;
- place, cancel, or modify live/paper trades;
- commit generated runtime outputs or secrets;
- define global contracts without routing them through `trading-manager`;
- invent shared fields/statuses/types without registry review;
- bypass accepted storage or manager lifecycle boundaries.
