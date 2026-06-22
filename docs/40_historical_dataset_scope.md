# Historical Dataset Scope

Status: accepted dataset-construction policy for offline historical training; live-routing constraints unchanged
Date: 2026-06-10

## Purpose

Historical model training needs broad, representative evidence. Live inference needs a narrower, current-route handoff. These are related but not identical.

The accepted rule is:

```text
historical training sampling universe != live inference routing universe
```

A model may train on a broader point-in-time sample universe than the candidate set it will receive in live operation. The broader training universe must still preserve chronology, availability timestamps, identity-safety rules, no future leakage, and downstream-boundary separation.

## Core Distinction

| Surface | Meaning | Constraint |
|---|---|---|
| Historical training sampling universe | Rows collected to fit, calibrate, validate, and test a model. | May be intentionally broad to improve coverage across regimes, sectors, events, liquidity states, and edge cases. |
| Live inference routing universe | Rows that reach a model during actual decision routing. | May be narrower because upstream models gate or prioritize the current candidate set. |

Training should not blindly copy live-routing filters when doing so would starve the model of useful contrast.

## Full-Minute Coverage Rule

Historical training should use every eligible minute as the point-in-time state ledger whenever required inputs can be built and label windows can mature. Full-minute coverage is the default because blank/no-action time is the dominant live state and must be represented during training.

Live invocation is separate. Execution may invoke optional components only when the current route needs them; for example, M05 can be called only after M04 produces an option-expression-relevant thesis. Historical training should still record M05 applicability state for the minute:

```text
optionable chain available -> M05 expression candidate row
structural no-listed-options / temporary no chain / crypto route -> M05 `non_optionable_underlying` or `optionable_chain_missing` surface status with direct-underlying/no-option expression row
```

The same pattern applies to events and governance:

```text
no accepted event -> M03 neutral/no-event state
no residual event concern -> M06 no_intervention state
uncertain attribution -> M06 low-confidence attribution state
```

Models may use loss masks, class weights, and evaluation buckets so rare positive cases remain visible. The mask changes how the row contributes to a specific objective; it must not erase the minute from the ledger.

## Global Training Rules

1. Broader sampling is allowed only for offline training/evaluation evidence, not for live routing bypass.
2. Every row must remain point-in-time with `available_time` and `tradeable_time` discipline.
3. Upstream outputs may be used as context features in historical training without becoming hard filters.
4. Training labels may look forward only from the row's tradeable time and only inside label/evaluation surfaces, never inference features.
5. Raw symbol/company identity remains audit/routing metadata where identity-safety is required; it must not become a memorized fitting feature.
6. Candidate thresholds, action triggers, and downstream execution routes are calibration/routing policies after scoring; they must not become default training-row admission filters.
7. Promotion evidence should report both broad historical generalization and live-route simulation performance when a model's live candidate set is narrower than its training sample universe.

## Dataset-Scope Matrix

| Model | Historical training sampling universe | Live inference routing universe |
|---|---|---|
| `M01 BackgroundContextModel` | Broad market, sector/industry, ETF/theme, cross-asset, volatility, liquidity, breadth, dispersion, correlation, and macro-sensitive context. | Current background context only; does not route targets or actions. |
| `M02 TargetStateModel` | Frozen point-in-time anonymous target pool across sectors, industries, styles, market caps, liquidity tiers, and crypto/context exceptions where accepted. | Targets routed from the reviewed realtime candidate universe and target metadata, with M01 context attached as conditioning evidence rather than candidate-universe membership. |
| `M03 EventStateModel` | Full-minute background/target state paired with accepted event/strategy-failure evidence when present and explicit neutral/no-event rows when absent. Includes observe-only, entry-block, exposure-cap, disable, and adverse-path examples when point-in-time labels exist. | Current M01/M02 state plus accepted event/strategy-failure evidence or explicit neutral/no-event state for routed candidates. |
| `M04 UnifiedDecisionModel` | Dense minute-level rows whenever M01-M03 context, quote/liquidity/borrow, costs, replay-safe portfolio/risk context, and exposure state can be constructed. Include trade and no-trade minutes, action alternatives, risk limits, churn, and adverse examples. | Current routed target/event/background stack plus replay-safe portfolio/risk and quote/liquidity context. |
| `M05 OptionExpressionModel` | Full-minute M04 thesis ledger with option-expression candidate rows when point-in-time option-chain snapshots exist, plus explicit surface-status rows for missing-chain, non-optionable, direct-underlying-only, and crypto routes. | Current M04 decision intent plus current option-chain context only when `optionable_chain_available`; missing-chain, direct-underlying, and crypto/non-optionable routes may bypass heavy option-chain work while preserving `optionable_chain_missing` or `non_optionable_underlying` status. |
| `M06 ResidualEventGovernanceModel` | Full-minute residual-governance rows, including event/no-event, intervention/no-intervention, effective/ineffective, sector-confirmed/sector-divergent, abnormal activity, news, earnings, macro, and price-action/false-breakout cases, joined point-in-time to the M04 direct-underlying decision. Attribution confidence is a state, not an admission prerequisite. | Residual events or neutral residual state attached to the current routed target/context stack and direct-underlying thesis for warning/intervention only; option-expression context is not required. |

## Target-State Special Rule

M02 must not be trained only on whatever live routing would have selected. That would remove the contrast needed to learn:

- strong targets in weak or unselected sectors;
- weak targets in strong sectors;
- sector-confirmed versus idiosyncratic target movement;
- sector-divergent target behavior;
- liquidity/tradability failures that upstream selection might hide;
- background+target lift over background-only baselines.

M01 context should remain attached to each M02 training row. It should be a point-in-time context block, not an unconditional historical-training filter.

## Evaluation Reporting

When training is broader than live routing, promotion evidence should separate:

| Evaluation view | Purpose |
|---|---|
| Broad historical generalization | Shows whether the model learned robust relationships across the wider sampled universe. |
| Live-route simulation | Shows expected performance after applying the actual upstream routing/gating policy. |
| Stress/subpopulation slices | Shows whether performance depends on sector class, liquidity tier, event type, regime, or routing inclusion/exclusion. |

Promotion can remain deferred if a model looks good only in the broad sample but fails under live-route simulation, or if it passes live-route simulation but shows unstable/leaky broad-sample evidence that undermines trust.
