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

For Layers 5 and later, the default training rule is dense minute-level state coverage whenever point-in-time inputs can be constructed. A model may run on demand in live routing, but historical training should still include action and no-action minutes so thresholds, capacity use, maintain decisions, and rejection reasons are calibrated against the distribution the live system will actually score.

## Global training rules

1. Broader sampling is allowed only for offline training/evaluation evidence, not for live routing bypass.
2. Every row must remain point-in-time with `available_time` and `tradeable_time` discipline.
3. Upstream outputs may be used as context features in historical training without becoming hard filters.
4. Training labels may look forward only from the row's tradeable time and only inside label/evaluation surfaces, never inference features.
5. Raw symbol/company identity remains audit/routing metadata where identity-safety is required; it must not become a memorized fitting feature.
6. Candidate thresholds, action triggers, and downstream execution routes are calibration/routing policies after scoring; they must not become default training-row admission filters.
7. Promotion evidence should report both broad historical generalization and live-route simulation performance when a layer's live candidate set is narrower than its training sample universe.

## Layer dataset-scope matrix

| Layer | Model | Historical training sampling universe | Live inference routing universe |
|---:|---|---|---|
| 1 | `MarketRegimeModel` | Broad market and cross-asset environment: market indexes, broad ETFs, rates, credit, dollar, commodities, volatility, liquidity, breadth, correlation, crypto/risk-appetite proxies where accepted. | Current broad market context only; does not route sectors or targets. |
| 2 | `SectorContextModel` | All reviewed sector/industry/theme baskets and relative-strength combinations across market regimes, including weak, strong, choppy, defensive, cyclical, and transition states. | Current sector/industry baskets scored under current Layer 1 context; may produce selected/prioritized handoff state. |
| 3 | `TargetStateVectorModel` | Broad anonymous target pool across sectors, industries, styles, market caps, liquidity tiers, and ETF/stock exposures. It is explicitly allowed to include targets outside the sectors Layer 2 would have selected at that time. | Targets routed from accepted upstream candidate construction, commonly from Layer 2 selected/prioritized sector baskets. |
| 4 | `EventFailureRiskModel` | Reviewed event/strategy-failure evidence paired with market/sector/target state and candidate strategy-family context. Includes no-event, observe-only, entry-block, exposure-cap, disable, and adverse-path examples when point-in-time labels exist. | Current reviewed Layer 1-3 stack plus accepted event/strategy-failure evidence for routed candidates. |
| 5 | `AlphaConfidenceModel` | Dense minute-level anonymous target-state rows from the accepted Layer 3 target universe, including strong setups, weak setups, no-edge rows, near-misses, negative/control rows, and event-risk-conditioned rows. | Current reviewed Layer 1-4 stack for eligible target-state rows; downstream candidate routing thresholds are calibration parameters, not training pre-filters. |
| 6 | `DynamicRiskPolicyModel` | Minute-level global risk-policy rows paired with market stress, systemic event-risk pressure, portfolio/account replay state, premium-budget pressure, and risk-budget labels; plus candidate/active-position conditioned rows when those contexts exist. | Current Layer 1 context plus portfolio/account replay context for global rows; optional Layer 5 alpha context for candidate/position rows; not a hard order limit. |
| 7 | `PositionProjectionModel` | Dense minute-level alpha/risk-policy rows from Layer 5/6, paired with simulated or historical current/pending position states, costs, risk budgets, and exposure constraints. Includes aligned, no-gap, reduce, add, flatten, and near-threshold rows. Scenarios may be constructed offline if point-in-time and label-safe. | Current alpha plus Layer 6 dynamic risk policy and actual/approved current and pending position context. |
| 8 | `UnderlyingActionModel` | Dense minute-level direct underlying/spot state rows whenever Layer 7 projection and underlying quote/liquidity context exist. Includes open/increase/reduce/close/cover/maintain/no-trade and adverse examples across stock, ETF, and crypto-style exposure states. | Current position projection for direct-underlying/spot expression candidates. |
| 9 | `TradingGuidanceModel` / `OptionExpressionModel` | Dense optionable-underlying minutes where point-in-time option-chain snapshots exist, plus direct-underlying/no-option rows when no valid option expression should be selected. Historical option-chain candidates should span IV regimes, expiries, deltas, liquidity, trends, chops, event-risk interventions, and no-expression cases. | Current Layer 8 underlying thesis plus current option-chain context when options are available; direct-underlying/crypto routes may bypass option-expression evidence. |
| 10 | `EventRiskGovernor` / `EventIntelligenceOverlay` | Cross-target/cross-sector residual-event rows, including event/no-event, effective/ineffective, sector-confirmed/sector-divergent, abnormal activity, news, earnings, macro, and price-action/false-breakout cases, joined point-in-time to the Layer 8 direct-underlying action thesis. | Residual events attached to the current routed target/context stack and underlying/spot thesis for warning/intervention only; option-expression context is not required. |

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
