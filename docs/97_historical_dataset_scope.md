# Historical Dataset Scope

Status: accepted dataset-construction policy for offline historical training; live-routing constraints unchanged
Date: 2026-05-10

## Purpose

Historical model training needs broad, representative evidence. Live inference needs a narrower, current-route handoff. These are related but not identical.

The accepted rule is:

```text
historical training sampling universe != live inference routing universe
```

A layer may train on a broader point-in-time sample universe than the candidate set it will receive in live operation. The broader training universe must still preserve chronology, availability timestamps, identity-safety rules, no future leakage, and downstream-boundary separation.

## Core distinction

| Surface | Meaning | Constraint |
|---|---|---|
| Historical training sampling universe | Rows collected to fit, calibrate, validate, and test a model layer. | May be intentionally broad to improve coverage across regimes, sectors, events, liquidity states, and edge cases. |
| Live inference routing universe | Rows that reach a layer during actual decision routing. | May be narrower because upstream layers gate or prioritize the current candidate set. |

Training should not blindly copy live-routing filters when doing so would starve the model of useful contrast. For example, Layer 3 live routing may receive targets from Layer 2 selected/prioritized sectors, while Layer 3 historical training may include targets from other sectors so the model learns sector-confirmed, sector-divergent, strong-in-weak-sector, and weak-in-strong-sector behavior.

## Global training rules

1. Broader sampling is allowed only for offline training/evaluation evidence, not for live routing bypass.
2. Every row must remain point-in-time with `available_time` and `tradeable_time` discipline.
3. Upstream outputs may be used as context features in historical training without becoming hard filters.
4. Training labels may look forward only from the row's tradeable time and only inside label/evaluation surfaces, never inference features.
5. Raw symbol/company identity remains audit/routing metadata where identity-safety is required; it must not become a memorized fitting feature.
6. Promotion evidence should report both broad historical generalization and live-route simulation performance when a layer's live candidate set is narrower than its training sample universe.

## Layer dataset-scope matrix

| Layer | Model | Historical training sampling universe | Live inference routing universe |
|---:|---|---|---|
| 1 | `MarketRegimeModel` | Broad market and cross-asset environment: market indexes, broad ETFs, rates, credit, dollar, commodities, volatility, liquidity, breadth, correlation, crypto/risk-appetite proxies where accepted. | Current broad market context only; does not route sectors or targets. |
| 2 | `SectorContextModel` | All reviewed sector/industry/theme baskets and relative-strength combinations across market regimes, including weak, strong, choppy, defensive, cyclical, and transition states. | Current sector/industry baskets scored under current Layer 1 context; may produce selected/prioritized handoff state. |
| 3 | `TargetStateVectorModel` | Broad anonymous target pool across sectors, industries, styles, market caps, liquidity tiers, and ETF/stock exposures. It is explicitly allowed to include targets outside the sectors Layer 2 would have selected at that time. | Targets routed from accepted upstream candidate construction, commonly from Layer 2 selected/prioritized sector baskets. |
| 4 | `AlphaConfidenceModel` | Broad state candidate rows from many market/sector/target contexts and both long/short directional orientations, including negative and low-confidence examples. | Current reviewed Layer 1-3 stack for routed candidates. |
| 5 | `PositionProjectionModel` | Candidate alpha rows paired with simulated or historical current/pending position states, costs, risk budgets, and exposure constraints. Scenarios may be constructed offline if point-in-time and label-safe. | Current alpha plus actual/approved current and pending position context. |
| 6 | `UnderlyingActionModel` | Direct stock/ETF action-outcome samples across broad exposure states, liquidity states, alpha strengths, and cost/risk conditions. Includes maintain/no-trade and adverse examples. | Current position projection for direct-underlying expression candidates. |
| 7 | `TradingGuidanceModel` / `OptionExpressionModel` | Base trading-guidance rows and optionable-underlying samples with historical option-chain snapshots across IV regimes, expiries, deltas, liquidity, trends, chops, and no-expression cases. | Current Layer 6 underlying thesis plus current option-chain context for optionable candidates only. |
| 8 | `EventRiskGovernor` / `EventIntelligenceOverlay` | Cross-target/cross-sector event rows, including event/no-event, effective/ineffective, sector-confirmed/sector-divergent, abnormal activity, news, earnings, macro, and price-action/false-breakout cases, joined point-in-time to base guidance. | Events attached to the current routed target/context stack and Layer 7 base guidance. |

## Layer 3 special rule

Layer 3 must not be trained only on whatever Layer 2 would have selected in live routing. That would remove the contrast needed to learn:

- strong targets in weak or unselected sectors;
- weak targets in strong sectors;
- sector-confirmed versus idiosyncratic target movement;
- sector-divergent target behavior;
- liquidity/tradability failures that upstream selection might hide;
- market+sector+target lift over market-only and market+sector baselines.

Layer 2 context should remain attached to each Layer 3 training row. It should be a point-in-time context block, not an unconditional historical-training filter.

## Evaluation reporting

When training is broader than live routing, promotion evidence should separate:

| Evaluation view | Purpose |
|---|---|
| Broad historical generalization | Shows whether the model learned robust relationships across the wider sampled universe. |
| Live-route simulation | Shows expected performance after applying the actual upstream routing/gating policy. |
| Stress/subpopulation slices | Shows whether performance depends on sector class, liquidity tier, event type, regime, or routing inclusion/exclusion. |

Promotion can remain deferred if a model looks good only in the broad sample but fails under live-route simulation, or if it passes live-route simulation but shows unstable/leaky broad-sample evidence that undermines trust.
