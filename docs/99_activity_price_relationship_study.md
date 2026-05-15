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

The first proof question is direction-neutral tradability: whether abnormal activity is followed by larger absolute price/path displacement. Downside paths are tradable too, so average signed return is only a secondary diagnostic.

Required direction-neutral label families:

```text
absolute_forward_return
forward_path_range
max_favorable_excursion
max_adverse_excursion
tradeable_excursion
forward_volatility_expansion
forward_gap_or_jump_abs
path_asymmetry
```

Required directional label families:

```text
activity_direction_bias
signed_forward_return
signed_directional_forward_return
forward_drawdown
forward_reversal
close_to_close_continuation
open_gap_followthrough
intraday_absorption_score
```

Rules:

- Primary activity-price proof should compare absolute forward moves and tradeable excursions between abnormal and non-abnormal windows.
- Directional alpha comes next. A strong downside relationship is useful if direction can be classified or hedged.
- Signed average forward return must not be used as the main acceptance metric because positive and negative tradable moves can cancel out.
- Direction labels are required for later model design, but they must be evaluated separately from direction-neutral tradability.

## Abnormality Coverage Completion Gate

The project must complete abnormality evidence coverage before treating any pilot as a directional conclusion. Partial slices are useful for debugging label shape, but they are not acceptance evidence.

Coverage must include all accepted abnormal-activity families before judgment:

```text
price_action_pattern
residual_market_structure_disturbance
microstructure_liquidity_disruption
option_derivatives_abnormality
```

For option-derived abnormality, coverage-complete means the study has point-in-time evidence for at least:

```text
call_put_side
aggressor_or_quote_side
ask_bid_touch_context
sweep_or_block_context
opening_or_closing_context
open_interest_or_oi_change
iv_level_and_change
skew_direction
term_structure_direction
underlying_confirmation_or_divergence
direction_confidence
```

Rules:

- If any required abnormality family is missing, outputs must be labeled `diagnostic_only_abnormality_incomplete`.
- Incomplete pilots may identify candidate hypotheses, data gaps, and label bugs, but must not produce a final bullish/bearish conclusion.
- Directional judgment must wait until the abnormality set is complete enough to distinguish demand, hedging, closing flow, dealer inventory, volatility demand, and liquidity disturbance.
- Cross-sectional testing begins after coverage is complete; simply adding more symbols with incomplete abnormality evidence does not solve the proof problem.

## Activity Direction Evidence

Some abnormal activity has natural directional orientation. The study must preserve this orientation rather than treating every activity token as directionless.

Accepted direction classes:

```text
bullish_activity
bearish_activity
neutral_activity
mixed_or_conflicting_activity
unknown_direction_activity
```

Directional evidence examples:

| Evidence type | Typical direction | Notes |
|---|---|---|
| call volume / call sweep / ask-side call buying surge | bullish | Requires option side/aggressor confidence; call volume alone can be hedging. |
| put volume / put sweep / ask-side put buying surge | bearish | Requires option side/aggressor confidence; put selling may be bullish, so quote side matters. |
| positive residual return or positive gap | bullish proxy | Price-derived and must be controlled for same-window tautology. |
| negative residual return or negative gap | bearish proxy | Price-derived and must be controlled for same-window tautology. |
| liquidity sweep high / false breakout / bull trap | bearish reversal proxy | Must be empirically tested; not assumed. |
| liquidity sweep low / false breakdown / bear trap | bullish reversal proxy | Must be empirically tested; not assumed. |
| IV expansion without call/put/skew side | direction unknown | Often indicates path/risk expansion rather than direction. |
| skew shift toward calls or puts | directional option evidence | Direction depends on skew definition and whether flow is buyer- or seller-initiated. |

### Option Activity Direction Study

Option activity must be handled as a directional-evidence study, not a generic volume spike. The same volume can mean different things depending on right, side, aggressor context, and whether the trade opens risk or closes/hedges risk.

Minimum option-direction evidence fields:

```text
option_right
trade_side_or_aggressor_side
ask_touch_ratio
bid_touch_ratio
sweep_or_block_context
trade_size
trade_notional
window_volume
open_interest_change
opening_or_closing_context
iv_change
skew_direction
term_structure_direction
direction_confidence
```

Initial option-direction hypotheses:

```text
ask_side_call_activity -> bullish_activity
ask_side_put_activity -> bearish_activity
bid_side_call_activity -> bearish_activity_or_call_selling
bid_side_put_activity -> bullish_activity_or_put_selling
call_put_ask_side_imbalance_positive -> bullish_activity
call_put_ask_side_imbalance_negative -> bearish_activity
iv_expansion_without_side -> unknown_direction_activity
call_skew_richening -> bullish_activity_or_upside_demand
put_skew_richening -> bearish_activity_or_downside_demand
```

Required option-direction comparisons:

1. call ask-side events vs non-event option windows;
2. put ask-side events vs non-event option windows;
3. call/put ask-side imbalance buckets;
4. IV-only expansion without side evidence;
5. sweep/block events vs ordinary prints;
6. opening-volume evidence vs ambiguous/closing-volume evidence;
7. option-direction evidence confirmed by underlying move vs option/underlying divergence.

The study should evaluate both underlying forward labels and option-forward labels when available:

```text
underlying_signed_directional_forward_return
underlying_absolute_forward_return
option_contract_signed_forward_return
option_contract_absolute_forward_return
implied_vol_forward_change
skew_forward_change
```

Important caveat: a call-buying surge is only directionally bullish when the system has enough side/aggressor/opening evidence. Otherwise it is an option-activity path-expansion signal with `unknown_direction_activity` or `review_required` direction.

Pilot evidence note: `/root/projects/trading-model/storage/option_direction_pilot_20260515_aapl/` contains a diagnostic AAPL one-date pilot using ThetaData option event timeline rows, Alpaca underlying daily bars, and ThetaData option OHLC snapshots. It validates the label shape but is not promotion evidence: one symbol/date/strike, duplicated same-day forward labels, no OI/skew/sweep/block context, and no calibrated direction confidence. The pilot also clarifies label policy: underlying directional returns are sign-adjusted by bullish/bearish hypothesis, while ask-side call/put option-contract payoff is measured as long-contract forward return and must not multiply put returns by the bearish sign.

Cross-section pilot note: `/root/projects/trading-model/storage/option_direction_cross_section_20260515/` extends the diagnostic slice to NVDA, JPM, XOM, LLY, and RKLB on the same event date. The headline result is mixed: ask-side CALL evidence is more promising than ask-side PUT evidence, especially on symbol-weighted 10d outcomes, but neither direction can be treated as a universal rule. Ask-side PUT activity was weak as a stable bearish signal in this slice. This remains `diagnostic_only_abnormality_incomplete`: it reinforces that option direction needs OI/opening-vs-closing, skew/term-structure, sweep/block, and confidence filters before judgment.

Directional proof metrics:

```text
activity_direction_bias_score
activity_direction_confidence_score
signed_directional_forward_return
directional_hit_rate
opposite_direction_failure_rate
mixed_direction_conflict_score
```

Rules:

- Direction must come from point-in-time activity evidence, not from future return labels.
- Option direction must distinguish call vs put, buy vs sell/aggressor side when available, sweep/block context, and whether the activity is opening or closing/hedging flow.
- If activity expands path but direction is weak, it can still be valuable for volatility, optionality, or risk-governor use.
- Directional proof must be stratified by activity type; e.g. call-buying evidence should not be evaluated together with IV-only expansion.

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

The key acceptance question is not whether abnormal windows have a higher signed average return. It is whether specific activity classes expand absolute forward paths or tradeable excursions after controls, and whether later stages can classify direction, reversal, continuation, or risk.

## Acceptance Standard

The proof gate can pass only if evidence shows:

```text
abnormality_coverage_complete
forward_price_path_relationship
incremental_residual_value
cross_sectional_non_story_stock_support
out_of_sample_stability
leakage_controls_passed
reviewed_failure_modes
```

`abnormality_coverage_complete` must be evaluated before accepting direction or promotion evidence. Without it, the result remains a data-coverage diagnostic even if a pilot has attractive returns.

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
