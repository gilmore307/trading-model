# Activity-Price Relationship Study

This study tests whether abnormal activity has a stable, point-in-time relationship to subsequent price/path outcomes across different company sizes, sectors, and event families.

It is the required proof gate before `event_activity_bridge` can be promoted into `EventActivityBridgeModel` or used as `EventRiskGovernor` risk-intervention evidence.

## Purpose

The project hypothesis is:

> Abnormal activity can standardize part of the relationship between hard-to-standardize events/news and future price or odds behavior.

The study must prove this without tautology. Price-derived activity cannot be validated against the same price interval that created it.

## Study Questions

1. Does abnormal activity predict or explain forward price/path labels after the detection window?
2. Does the relationship remain after controlling for market, sector, peer, and target-state context?
3. Does event-confirmed abnormal activity behave differently from abnormal activity with no visible event?
4. Does pre-event abnormal activity provide useful latent-event hazard evidence?
5. Do option/liquidity activity legs add value beyond ordinary price/volume activity?
6. When prediction-market data is later available, does odds activity confirm or diverge from securities activity in a useful way?

## Cohort Design

The study must be cross-sectional. A single story stock can be used for debugging, but not for acceptance.

### Size Buckets

```text
mega_large_cap
large_cap
mid_cap
small_cap
micro_or_speculative_cap
```

### Sector / Theme Buckets

Initial study buckets:

```text
technology_platform
semiconductor_ai
financials_bank_or_broker
energy_commodity
healthcare_biotech
industrial_defense_aerospace
communications_satellite
consumer_retail
crypto_sensitive
```

### Candidate Pilot Basket

This is a pilot basket, not a permanent universe. Symbols may be replaced when liquidity/news coverage is insufficient.

| Bucket | Example symbols | Rationale |
|---|---|---|
| mega/technology | AAPL, MSFT | deep liquidity, many news events, strong controls needed |
| mega/semiconductor_ai | NVDA, AMD | high event sensitivity, options-rich |
| large/financials | JPM, COIN | bank/market-structure and crypto-sensitive event channels |
| large/energy | XOM, CVX | commodity and geopolitical event sensitivity |
| large/healthcare | LLY, PFE | FDA/clinical/earnings style event contrast |
| mid/industrial-defense | RKLB, ACHR | aerospace/defense/news-contract sensitivity |
| small/communications-satellite | ASTS | financing/FCC/launch/partnership event sensitivity |
| small/defense-drone | RCAT | relatively pure drone/government-contract pilot case |
| small/consumer-retail | CAVA, ELF | consumer/earnings/social-attention contrast |
| speculative/biotech | VKTX, SAVA | clinical/regulatory event sensitivity; review for liquidity/noise |

Selection rules:

- Exclude symbols with too little daily volume or too sparse news coverage for the chosen window.
- Exclude symbols where corporate actions, listing changes, or missing data make labels unreliable unless explicitly handled.
- Keep at least one broad-market ETF and one sector/theme ETF control per bucket.
- Prefer symbols with both quiet periods and event-heavy periods.

## Event / Activity Classes

Activity classes follow the accepted abnormal-activity taxonomy:

```text
price_action_pattern
residual_market_structure_disturbance
microstructure_liquidity_disruption
option_derivatives_abnormality
```

Bridge relation classes:

```text
pre_event_precursor
co_event_reaction
post_event_absorption
event_activity_divergence
unresolved_latent_hazard
```

Event families should be evaluated separately before aggregate conclusions:

```text
earnings_or_guidance
analyst_rating_or_price_target
contract_award_or_customer_order
regulatory_or_legal
financing_or_offering
product_or_partnership
macro_policy_or_geopolitical
short_report_or_investigative_claim
clinical_or_fda
prediction_market_resolution_related
```

## Windows

The study must separate windows:

```text
activity_detection_window
event_availability_window
forward_label_window
```

Initial horizons:

```text
5m
30m
1h
1d
5d
20d
```

Daily-only runs may use `1d`, `5d`, and `20d` first. Intraday runs should be added for the cleanest event cases.

## Forward Labels

Required forward label families:

```text
forward_return
forward_drawdown
forward_reversal
forward_volatility_expansion
forward_gap_or_jump
path_asymmetry
```

Recommended additional diagnostics:

```text
max_favorable_excursion
max_adverse_excursion
close_to_close_continuation
open_gap_followthrough
intraday_absorption_score
```

## Controls

At minimum, evaluate abnormal activity after controlling for:

- broad market return and volatility context;
- sector/theme ETF return context;
- peer basket return context;
- existing target-state features;
- ordinary bars, volume, liquidity, volatility, gap, and trend features;
- scheduled event calendar shells;
- time-of-day, day-of-week, and month effects;
- broad-market liquidity/volatility regime;
- prior momentum and prior drawdown.

## Required Comparisons

For each symbol/bucket/event family, compare:

1. all eligible windows;
2. abnormal activity windows;
3. non-abnormal windows;
4. event-only windows;
5. event + abnormal windows;
6. abnormal-without-visible-event windows;
7. pre-event abnormal windows later explained by event;
8. event/activity divergence windows.

The key acceptance question is not whether abnormal windows are more volatile. It is whether specific activity classes improve forward path labels after controls.

## Acceptance Standard

The proof gate can pass only if evidence shows:

```text
forward_price_path_relationship
incremental_residual_value
cross_sectional_non_story_stock_support
out_of_sample_stability
leakage_controls_passed
reviewed_failure_modes
```

A convincing result should identify where the signal works and where it does not. It does not need every sector and every activity class to work.

Fail conditions:

- effect exists only in one story stock;
- activity only describes same-window price movement;
- signal disappears after market/sector/ordinary-feature controls;
- signal is dominated by liquidity noise in small caps;
- labels depend on hindsight event availability;
- results are unstable across time splits.

## Promotion Path

If the study passes:

1. create `EventActivityBridgeModel` as a candidate layer;
2. define bridge vector outputs and deterministic baseline scorer;
3. run family-specific and cross-family evaluations;
4. only then allow `EventRiskGovernor` to consume bridge outputs for risk intervention.

If the study fails:

- abnormal activity remains descriptive/provenance evidence;
- no model-layer promotion;
- retain useful event-review diagnostics only.
