# Decisions

This file records the current accepted decisions for `trading-model`. Historical route changes remain in Git history; this file describes the live architecture directly.

## D001 - Repository boundary

Date: 2026-04-25
Status: Accepted

`trading-model` owns offline modeling research, validation, model-local outputs, promotion evidence, and decision-record prototypes for the trading decision stack.

It does not own raw source acquisition, global registry authority, durable storage policy, scheduling/lifecycle routing, live/paper order placement, broker/account mutation, dashboards, secrets, or committed generated runtime artifacts.

Cross-repository names, shared fields, artifact types, statuses, templates, and contracts must be routed through `trading-manager` before other repositories depend on them.

## D002 - Direction-neutral model stack

Date: 2026-04-27
Status: Accepted; revised by V2.2 on 2026-05-05

`trading-model` is the offline modeling home for the direction-neutral tradability decision stack:

| Layer | Model | Stable id | Role |
|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_regime_model` | Broad market tradability/regime context state. |
| 2 | `SectorContextModel` | `sector_context_model` | Market-context-conditioned sector/industry tradability context. |
| 3 | `TargetStateVectorModel` | `target_state_vector_model` | Direction-neutral target context for anonymized target candidates; anonymous candidate construction is Layer 3 preprocessing. |
| 4 | `AlphaConfidenceModel` | `alpha_confidence_model` | Reviewed state stack to adjusted alpha direction, strength, expected residual return, confidence, reliability, path quality, reversal/drawdown risk, and alpha tradability. |
| 5 | `PositionProjectionModel` | `position_projection_model` | Final adjusted alpha plus current/pending position, cost, and risk context to projected target holding state. |
| 6 | `UnderlyingActionModel` | `underlying_action_model` | Direct stock/ETF planned action thesis: eligibility, planned action type, planned exposure change, entry/target/stop/time-stop, and trading-guidance handoff. |
| 7 | `TradingGuidanceModel` / `OptionExpressionModel` | `trading_guidance_model` / `option_expression_model` | Base trading guidance and optional option-expression selection from the underlying thesis and option-chain context; broker mutation remains outside `trading-model`. |
| 8 | `EventRiskGovernor` / `EventIntelligenceOverlay` | `event_risk_governor` | Point-in-time event-risk intervention after base trading guidance; may block/cap/review guidance but must not mutate broker/account state. |

Live/paper order placement remains outside this repository and no layer should be renamed live `ExecutionModel`.

## D003 - Current structure separates market, sector, and target work

Date: 2026-05-02
Status: Accepted

The current route is:

```text
MarketRegimeModel
  -> market_context_state

SectorContextModel
  -> sector_context_state

TargetStateVectorModel
  -> Layer 3 preprocessing: anonymous target candidate builder
  -> target_candidate_id
  -> anonymous_target_feature_vector
  -> target_context_state

AlphaConfidenceModel
  -> alpha_confidence_vector

PositionProjectionModel
  -> position_projection_vector

UnderlyingActionModel
  -> underlying_action_plan / underlying_action_vector

TradingGuidanceModel / OptionExpressionModel
  -> trading_guidance / option_expression_plan / expression_vector

EventRiskGovernor / EventIntelligenceOverlay
  -> event_risk_intervention / event_context_vector
```

Hard separation rules:

- Layer 1 describes broad market state only.
- Layer 2 describes sector/industry basket behavior under broad market state.
- Layer 3 is the first target-state layer.
- Final target/security choice must be made downstream from accepted target-state evidence, not from raw identity.
- Model-facing fitting rows for target work must anonymize ticker/company identity.
- Real symbols may remain in audit/routing metadata and decision records, but not in model-facing identity features.

## D004 - Layer 1 output is market context, not selection

Date: 2026-05-01
Status: Accepted

`MarketRegimeModel` V2.2 outputs a continuous point-in-time broad `market_context_state` keyed by `available_time`.

The physical output table is:

```text
trading_model.model_01_market_regime
```

Current model-facing state score keys:

```text
1_market_direction_score
1_market_direction_strength_score
1_market_trend_quality_score
1_market_stability_score
1_market_risk_stress_score
1_market_transition_risk_score
1_breadth_participation_score
1_correlation_crowding_score
1_dispersion_opportunity_score
1_market_liquidity_pressure_score
1_market_liquidity_support_score
1_coverage_score
1_data_quality_score
```

Docs, model-facing payloads, and physical SQL columns use the same compact `1_*` contract. SQL writers quote numeric-leading identifiers where required instead of creating `layer01_*` aliases. Old `1_*_factor` groups remain model-local signal groups and explainability/evidence sources, not public downstream output fields.

Layer 1 must not output sector rankings, ETF rankings, stock candidates, strategy labels, option contracts, position/portfolio actions, future-return labels, or pre-assigned ETF/sector behavior classes.

ETF/sector labels such as `growth`, `defensive`, `cyclical`, `inflation_sensitive`, or `safe_haven` are not Layer 1 facts. If useful, they are Layer 2 posterior interpretations inferred from point-in-time behavior, holdings, and market-state-conditioned trend stability.

## D005 - Layer 1 evidence and evaluation maturation

Date: 2026-05-02
Status: Accepted

Layer 1 structure is settled for V2.2. Remaining Layer 1 work is evidence depth and real-sample promotion review, not boundary redesign.

For each internal signal group and public state score, maintain `src/models/model_01_market_regime/evidence_map.md` as the feature-to-state evidence map classifying feature families as:

- primary evidence;
- diagnostic evidence;
- quality evidence;
- evaluation-only evidence;
- intentionally unused evidence.

Layer 1 evaluation must test:

- point-in-time correctness;
- rolling/expanding stability;
- responsiveness to real market transitions;
- explanatory value for Layer 2 sector trend-stability calibration;
- usefulness for `OptionExpressionModel` contract constraints;
- usefulness for downstream reviewed position projection, underlying-action thesis, option expression, and risk-policy handoff without turning Layer 1 into an action model.

`market_context_state` is the accepted downstream semantic surface for current Layer 1 state-score fields.

## D006 - Layer 2 is sector/industry trend-stability, not final stock selection

Date: 2026-05-02
Status: Accepted

`SectorContextModel` V1 outputs a sector/industry context state. It studies which sector/industry ETF baskets have stable, tradable trend behavior under each broad market context.

Layer 1 market-property factors are conditioning context only. Layer 2 must learn a separate conditional behavior vector for each ETF/basket under similar market backgrounds; it must not reuse Layer 1 factor names as ETF style fields.

Conditional behavior fields should prefer signed axes over duplicated opposite fields: positive and negative values represent opposite behavior on the same reviewed axis, and magnitude represents strength. If later evidence needs total intensity separately, add a separate intensity field rather than splitting every opposite pair by default.

Conceptual output:

```text
sector_context_state[available_time, sector_or_industry_symbol]
```

Planned physical output:

```text
trading_model.model_02_sector_context
```

The V1 field contract is owned by `src/models/model_02_sector_context/sector_context_state_contract.md` until implementation/evaluation proves which names should be shared through the registry.

Core state blocks:

```text
2_sector_observed_behavior_vector
2_sector_attribute_vector
2_sector_conditional_behavior_vector
2_sector_trend_stability_vector
2_sector_tradability_vector
2_sector_risk_context_vector
2_eligibility_state
2_sector_handoff_state
optional 2_sector_selection_parameter
```

Physical SQL columns for these model-facing keys use the same compact `2_*` names. SQL writers quote numeric-leading identifiers where required instead of creating `layer02_*` aliases.

Layer 2 may select or block sector/industry baskets for downstream candidate construction. It must not choose final stocks, entry timing, strategy parameters, option contracts, final size, or portfolio weights.

## D007 - ETF holdings move to downstream candidate construction

Date: 2026-05-02
Status: Accepted

ETF holdings and `stock_etf_exposure` are not core inputs to Layer 2 sector behavior modeling. Layer 2 should learn ETF/basket conditional behavior from price/relative-strength/volatility/correlation/tradability/event evidence under similar market backgrounds.

After Layer 2 selects or prioritizes sector/industry baskets, the anonymous target candidate builder may use ETF holdings and `stock_etf_exposure` to transmit selected baskets into a stock candidate universe. Layer 3 target-state construction must still consume anonymous target feature vectors rather than raw ticker/company identity.

## D008 - Target fitting must use anonymous target candidates

Date: 2026-05-02
Status: Accepted

`TargetStateVectorModel` and later target-aware layers may evaluate target candidates only through model-facing anonymous features.

Allowed in model-facing fitting vectors:

- target behavior shape;
- liquidity and tradability shape;
- sector context state;
- broad market context state;
- event/risk/cost context;
- strategy compatibility features.

Excluded from model-facing fitting vectors:

- raw ticker identity;
- company identity;
- memorized symbol-specific historical winner labels.

Real symbols may remain in audit/routing metadata and final decision records.

## D009 - OptionExpressionModel V1 is single-leg long options only

Date: 2026-04-28
Status: Accepted

`OptionExpressionModel` V1 supports only:

- stock/ETF direct expression as a comparison or fallback;
- long call;
- long put.

V1 must not choose debit spreads, calendars, diagonals, straddles, strangles, condors, butterflies, ratio spreads, or naked short options.

The model must use timestamped option-chain snapshots, bid/ask, liquidity, IV, Greeks, conservative fill assumptions, and market-context constraints such as DTE, delta/moneyness, IV/vega/theta tolerance, and no-trade filters.

Layer-numbering update: after D047, this decision is preserved as Layer 8 `OptionExpressionModel` / trading-guidance context after Layer 7 `UnderlyingActionModel`. Current physical implementation names use `model_08_option_expression`.

## D010 - Model governance and promotion evidence stay model-local until manager control-plane acceptance

Date: 2026-05-01
Status: Superseded by D036

Model evaluation evidence may stay model-local until it is accepted by manager-owned control-plane review. Durable promotion decisions, activation, rollback, and production pointers are no longer model-owned.

## D036 - Promotion decisions and activation belong to trading-manager

Date: 2026-05-09
Status: Accepted

`trading-model` owns model output generation, labels, evaluation computation, promotion metrics, candidate evidence packages, and reviewer artifacts.

`trading-manager` owns the unified `model_promotion_review` request path, durable review decisions, activation records, rollback references, and cross-layer production gates. Model-side review scripts must not persist manager-control-plane promotion rows or activate production pointers.

## D011 - Model output keys carry layer ownership prefixes

Date: 2026-05-02
Status: Accepted

Model-facing output vectors and output fields must carry their layer owner in the field name so downstream contracts cannot confuse similarly named concepts across layers.

Rules:

- Layer 1 model-facing output keys use compact `1_*` names, for example `1_market_trend_quality_score`.
- Layer 2 model-facing output keys use compact `2_*` names, for example `2_sector_context_state` and `2_sector_tradability_score`.
- Deterministic data evidence fields from `trading-data` do not receive model-layer prefixes merely because a model consumes them.
- Docs, model-facing payloads, and physical SQL columns use the same compact names. SQL writers should quote numeric-leading identifiers where required instead of storing semantic aliases such as `layer01_*` or `layer02_*`.

## D012 - Anonymous target candidate builder owns the Layer 3 candidate-preparation identity boundary

Date: 2026-05-02
Status: Accepted

The boundary between `SectorContextModel` and `TargetStateVectorModel` is a Layer 3 anonymous target candidate builder, not a peer model layer and not direct ticker-aware target-state fitting.

The model-local V1 contract is owned by:

```text
src/models/model_03_target_state_vector/anonymous_target_candidate_builder/target_candidate_builder_contract.md
```

The builder expands Layer 2 selected/prioritized sector or industry baskets into target candidates using point-in-time ETF holdings, `stock_etf_exposure`, target-local behavior, liquidity/tradability, event/risk, cost, optionability, and quality evidence.

It produces separate surfaces:

```text
model-facing: target_candidate_id + anonymous_target_feature_vector + context refs
metadata: audit/routing symbol references and source evidence refs
```

`target_candidate_id` is a row key only. It must not expose raw ticker/company identity and must not become a categorical fitting feature for Layer 3.

Real symbols may remain recoverable through audit/routing metadata, but that metadata must not be joined into model-facing fitting vectors except through reviewed non-identity evidence fields.

## D013 - Rename Layer 2 to SectorContextModel

Date: 2026-05-03
Status: Accepted

`SecuritySelectionModel` is no longer the accepted Layer 2 name because Layer 2 does not select final securities. Layer 2 models sector/industry basket context under the current broad market background, then hands selected/prioritized baskets to the anonymous target candidate builder.

Accepted canonical names:

- Class/display: `SectorContextModel`
- Stable id: `sector_context_model`
- Physical output table term: `model_02_sector_context`
- Conceptual output: `sector_context_state`

Retire active-use references to `SecuritySelectionModel`, `security_selection_model`, and `model_02_security_selection`. Historical decision text may mention them only as superseded terms.


## D014 - Model outputs split into output, explainability, and diagnostics artifacts

Date: 2026-05-03
Status: Accepted

Model-layer outputs should preserve downstream stability without discarding review detail. Each implemented model layer should therefore separate three physical artifacts:

```text
model_NN_<layer_slug>
model_NN_<layer_slug>_explainability
model_NN_<layer_slug>_diagnostics
```

The primary `model` artifact is the narrow downstream dependency surface: identity, stable state, handoff, and eligibility/quality summary fields. `explainability` owns human-review internals such as feature/factor attribution, observed behavior, inferred attributes, conditional behavior detail, contributing evidence, and reason-code detail. `diagnostics` owns acceptance, monitoring, and gating evidence such as freshness, missingness, standardization, liquidity/spread/optionability, event/gap/volatility/correlation stress, baseline comparison, refit stability, and no-future-leak checks.

Downstream production logic should not hard-depend on explainability or diagnostics fields without a later reviewed promotion decision.

## D015 - Promotion review uses a complete evidence package, not metrics alone

Date: 2026-05-03
Status: Accepted

Model promotion review must continue to use the full model-governance evidence chain rather than treating `model_promotion_metric` as a standalone decision surface.

The durable review flow is:

```text
model_dataset_snapshot
  ├─ model_dataset_split
  ├─ model_eval_label
  └─ model_eval_run
        └─ model_promotion_metric
```

`model_promotion_metric` owns the measured promotion scores. The surrounding dataset/evaluation tables own the context that makes those scores reviewable: the frozen data snapshot, point-in-time split windows, label/horizon construction, and the specific evaluation run that produced the metrics.

Agent or human promotion review should therefore receive a candidate evidence package rooted in `model_promotion_candidate` and backed by `model_eval_run`, including metric values plus thresholds, baseline comparison, split-stability evidence, leakage/no-future checks, and dataset/label provenance. Missing real-data evaluation, thresholds, baseline/stability/leakage evidence, or dataset/label context is grounds to defer promotion rather than approve.

## D016 - Layer 3 reset to TargetStateVectorModel

Date: 2026-05-04
Status: Accepted

Layer 3 is `TargetStateVectorModel`.

The active Layer 3 purpose is to construct an anonymous target state vector from three inspectable blocks:

1. Layer 1 market state;
2. Layer 2 sector/industry state;
3. target-local board/tape/liquidity state.

Layer 3 must focus on finding the relationship between target market state and future tradeable outcomes. Strategy-family and parameter-variant grids are frozen as legacy research and must not be expanded as the active Layer 3 boundary. Strategy/variant selection may return later only as a downstream layer or probe after target-state relationships are accepted.

## D017 - Three-state model uses direction-neutral tradability semantics

Date: 2026-05-05
Status: Accepted contract direction

The Market/Sector/Target state stack should rank state tradability, not long-only strength. Direction is a signed state property; positive direction is not inherently better than negative direction.

Layer 2 `SectorContextModel` must separate:

- signed sector direction evidence;
- trend quality and stability;
- transition/noise/crowding risk;
- liquidity/tradability;
- row reliability, coverage, and data quality;
- `2_sector_handoff_state` from `2_sector_handoff_bias`.

A sector can therefore be `selected` with `short_bias` when its downtrend state is clean, stable, liquid, and low-transition-risk. Conversely, a rising sector can be watched or blocked when it is noisy, fragile, crowded, illiquid, or poorly evidenced.

Layer 3 `TargetStateVectorModel` must make the same separation for anonymous target candidates. `3_target_direction_score_<window>` is current-state direction evidence only. It is not alpha confidence, not position size, and not a trading action. `3_tradability_score_<window>` is direction-neutral and must be validated on long-bias and short-bias cases separately.

Signed labels may be used for direction-neutral evaluation, but the orientation sign must come from deterministic point-in-time state evidence or from an out-of-sample upstream prediction. It must not be derived from the same fitted target being evaluated.

Post-D047 update: Layer 4 now owns EventFailureRiskModel failure-risk conditioning; Layer 5 owns alpha-confidence calibration; Layers 6-8 own position projection, direct-underlying action, and trading guidance / option expression; Layer 9 owns residual event-risk intervention. Layer 3 remains a state/context model.

## D018 - Vector taxonomy and Layer 3 preprocessing boundary

Date: 2026-05-05
Status: Accepted

The V2.2 three-layer tradability design uses a strict vocabulary split:

- `feature_*` surfaces are deterministic point-in-time inputs owned by `trading-data`.
- `*_feature_vector` values are model-facing input vectors.
- `*_state` values are narrow current-state model outputs.
- `*_state_vector` is reserved for an accepted block-structured state output such as Layer 3 `target_context_state`.
- `*_score` fields are scalar dimensions and must not silently combine direction, quality, tradability, confidence, and position size.
- `*_diagnostics` and `*_explainability` are support surfaces unless promoted separately.
- `*_label` / `*_outcome` values are training/evaluation-only and must never enter inference vectors.

Anonymous target candidate construction is Layer 3 preprocessing and sample organization. It is not a separate model, not a fourth layer, not Layer 2.5, and not a peer to `TargetStateVectorModel`.

`anonymous_target_feature_vector` is the Layer 3 model-facing input vector produced by preprocessing. `target_context_state` is the Layer 3 conceptual model output. Audit/routing metadata, including real symbol references, remains outside model-facing vectors.

Layer 1 now uses V2.2 market-tradability semantics: market direction, direction strength, trend quality, stability, risk stress, transition risk, breadth participation, correlation/crowding, dispersion opportunity, liquidity pressure/support, coverage, and data quality. Current `1_*_factor` names are model-local signal groups and evidence sources only; the public downstream contract is the `market_context_state` score set.

## D019 - Durable manager/storage contracts are deferred until the full model stack is designed

Date: 2026-05-06
Status: Accepted

State-vector semantics and model-local outputs may continue to mature inside `trading-model`, but final artifact, manifest, ready-signal, request, durable receipt, shared storage root, and SQL/storage destination contracts wait until all model layers are designed and `trading-manager` development begins.

This keeps Layer 1-8 model design from being constrained by premature manager/storage interface decisions. Registry state-vector values remain reviewed naming/semantic references; they do not by themselves finalize durable manager/storage contracts.

## D020 - Superseded EventRiskGovernor pre-alpha ordering

Date: 2026-05-06
Status: Superseded by D039 on 2026-05-15

This decision preserved the earlier EventRiskGovernor-as-Layer-4 route. D039 later moved event governance after the base trading stack, and D047 is now authoritative for exact numbering: EventFailureRiskModel is Layer 4, AlphaConfidenceModel is Layer 5, and EventRiskGovernor / EventIntelligenceOverlay is Layer 9 after base trading guidance.

Previous layer order:

```text
market_context_state
  -> sector_context_state
  -> target_context_state
  -> event_context_vector
  -> alpha_confidence_vector
  -> position_projection_vector
  -> underlying_action_plan / underlying_action_vector
  -> option_expression_plan / expression_vector
```

Layer 9 consumes point-in-time event evidence such as legacy `source_09_event_risk_governor`, equity abnormal activity events, option abnormal activity events, macro/calendar events, news, and filings. It must preserve `event_time`, `available_time`, canonical-event identity, deduplication status, source priority, scope, references, and point-in-time availability.

The former hard-upstream event route must not be used as active layer ordering. Event-risk governance is now Layer 9, except for reviewed event-failure factors promoted into Layer 4.

## D021 - AlphaConfidenceModel adjusted alpha-confidence boundary

Date: 2026-05-07
Status: Accepted

Layer-numbering update after D047: `AlphaConfidenceModel` is Layer 5 with canonical model id `alpha_confidence_model`, output `alpha_confidence_vector`, current physical surface `model_05_alpha_confidence`, and `5_*` score prefixes.

AlphaConfidenceModel consumes the reviewed Layer 1/2/3 state stack plus Layer 4 event-failure-risk conditioning when applicable. It is the first layer allowed to convert accepted point-in-time state/context evidence into horizon-aware alpha judgment. Raw event intelligence is not a hard upstream correction input; Layer 9 may later intervene on base guidance. AlphaConfidenceModel owns alpha direction, alpha strength, expected residual return, alpha confidence, signal reliability, path quality, reversal risk, drawdown risk, and alpha-level tradability.

AlphaConfidenceModel keeps two output tiers separate:

- base/unadjusted alpha diagnostics from Layer 1/2/3 only, for research, audit, and event-adjustment attribution;
- final adjusted `alpha_confidence_vector`, which is the only default Layer 6-facing Layer 5 output.

AlphaConfidenceModel must keep these boundaries explicit:

```text
target direction evidence != alpha confidence
event direction bias != alpha confidence
confidence != expected residual return
expected residual return != target exposure
risk != no-trade instruction
base alpha != final adjusted alpha
alpha tradability != trading signal
alpha confidence != option expression
alpha confidence != final action
```

AlphaConfidenceModel must not emit buy/sell/hold, final action, target exposure, position size, account-risk allocation, option contract, strike, DTE, delta, order type, or broker/account mutation. Layer 6 owns position projection and target exposure state. Layer 7 owns planned direct-underlying action. Layer 8 owns trading guidance / option expression. Layer 9 owns residual event-risk governance.

AlphaConfidenceModel V1 uses the synchronized `5min`, `15min`, `60min`, and `390min` horizons for the accepted final 9 score families: direction, strength, expected return, confidence, reliability, path quality, reversal risk, drawdown risk, and alpha tradability. Future changes to horizon grids or score families require evaluation evidence and registry review.


## D022 - PositionProjectionModel target holding-state boundary

Date: 2026-05-07
Status: Accepted

Layer-numbering update: `PositionProjectionModel` is Layer 6 with canonical model id `position_projection_model` and conceptual output `position_projection_vector`; the physical implementation and score prefixes now use current `model_06` / `6_*` names.

PositionProjectionModel maps final adjusted alpha confidence to projected target holding state under current account/portfolio context. It consumes `alpha_confidence_vector`, current position state, pending position state, point-in-time position-level friction, portfolio exposure context, risk-budget context, and policy gates.

The accepted V1 core output families are:

```text
6_target_position_bias_score_<horizon>
6_target_exposure_score_<horizon>
6_current_position_alignment_score_<horizon>
6_position_gap_score_<horizon>
6_position_gap_magnitude_score_<horizon>
6_expected_position_utility_score_<horizon>
6_cost_to_adjust_position_score_<horizon>
6_risk_budget_fit_score_<horizon>
6_position_state_stability_score_<horizon>
6_projection_confidence_score_<horizon>
```

PositionProjectionModel uses synchronized horizons `5min`, `15min`, `60min`, and `390min`. It may expose handoff summary fields such as dominant projection horizon, horizon conflict state, resolved target exposure, resolved position gap, resolution confidence, and reason codes so the downstream UnderlyingActionModel does not re-solve horizon conflicts.

Accepted invariants:

```text
target exposure != order quantity
position gap != execution instruction
projection confidence != alpha confidence
position projection vector != final action
```

PositionProjectionModel must not emit buy/sell/hold/open/close/reverse, choose instruments, read option chains, choose strike/DTE/Greeks, route orders, or mutate broker/account state. Layer 7 owns planned direct-underlying action thesis; Layer 8 owns trading guidance / option expression; live/paper broker mutation remains outside `trading-model`.

## D023 - UnderlyingActionModel planned direct-underlying action boundary

Date: 2026-05-07
Status: Accepted

Layer-numbering update: `UnderlyingActionModel` is Layer 7 with canonical model id `underlying_action_model` and primary output `underlying_action_plan`; its score/vector output is `underlying_action_vector`. The physical implementation and score prefixes now use current `model_07` / `7_*` names.

UnderlyingActionModel converts current state, final adjusted alpha confidence, and target holding-state projection into a direct stock/ETF offline action thesis. It consumes `alpha_confidence_vector`, `position_projection_vector`, current/pending underlying exposure, underlying quote/liquidity/borrow state, risk-budget context, and point-in-time policy gates.

The accepted V1 score families are:

```text
7_underlying_trade_eligibility_score_<horizon>
7_underlying_action_direction_score_<horizon>
7_underlying_trade_intensity_score_<horizon>
7_underlying_entry_quality_score_<horizon>
7_underlying_expected_return_score_<horizon>
7_underlying_adverse_risk_score_<horizon>
7_underlying_reward_risk_score_<horizon>
7_underlying_liquidity_fit_score_<horizon>
7_underlying_holding_time_fit_score_<horizon>
7_underlying_action_confidence_score_<horizon>
```

UnderlyingActionModel uses synchronized horizons `5min`, `15min`, `60min`, and `390min`. It may expose resolved plan fields such as `7_resolved_underlying_action_type`, action side, dominant horizon, trade eligibility, trade intensity, entry quality, action confidence, and reason codes so downstream trading guidance / option expression does not re-solve the direct-underlying thesis.

Accepted planned action types are:

```text
open_long
increase_long
reduce_long
close_long
open_short
increase_short
reduce_short
cover_short
maintain
no_trade
bearish_underlying_path_but_no_short_allowed
```

`maintain` and `no_trade` are distinct. `maintain` means an existing state is still aligned or not worth adjusting; `no_trade` means no new direct-underlying operation should be initiated.

UnderlyingActionModel must use effective current underlying exposure:

```text
effective_current_underlying_exposure
= current_underlying_exposure
  + pending_underlying_exposure * pending_fill_probability_estimate
```

Accepted invariants:

```text
planned underlying action != broker order
planned quantity != final order quantity
entry plan != order type
stop_loss_price != broker stop order
take_profit_price != broker limit order
underlying price-path thesis != guaranteed outcome
underlying action plan != option expression
underlying action plan != live execution
```

UnderlyingActionModel must not emit broker order fields, order type, route, time-in-force, send/cancel/replace flags, broker order ids, option strike/DTE/delta/Greeks, specific option contract refs, or broker/account mutations. Layer 8 owns trading guidance / option expression. `trading-execution` owns broker-order lifecycle.

## D024 - OptionExpressionModel owns offline option expression only

Date: 2026-05-07
Status: Accepted

Layer-numbering update after D047: `OptionExpressionModel` is the accepted Layer 8 option-expression implementation surface (`model_08_option_expression`) under the trading-guidance boundary.

It consumes Layer 7 `underlying_action_plan` / `underlying_action_vector` handoff plus point-in-time option-chain context and outputs:

```text
option_expression_plan
expression_vector
```

V1 expression types are:

```text
long_call
long_put
no_option_expression
```

V1 may select a point-in-time option contract reference and contract constraints for the expression. This is model output, not a broker order.

Accepted invariants:

```text
option expression != broker order
contract_ref != broker order id
selected_contract != send order
contract constraints != route / time-in-force
premium risk plan != account mutation
expression confidence != final approval
Layer 8 offline plan != live execution
```

Layer 8 must not emit broker order type, route, time-in-force, send/cancel/replace flags, final order quantity, broker order ids, or account mutation fields. Multi-leg structures are deferred beyond V1. `trading-execution` remains the owner of live/paper broker mutation.

## D024A - Layer 8 historical option bucket defaults

Date: 2026-05-10
Status: Accepted

Layer 8 option-expression bucket construction uses near-to-far listed expirations: current listed week first, then next listed week, then the following listed week, continuing outward only when coverage policy requires it.

For each selected target, the strike bucket is the listed-strike corridor from current underlying reference price to the Layer 7 underlying-action target price plus three actual listed strike levels below the corridor and three actual listed strike levels above it. Example: current `95`, target `100`, one-dollar listed strikes -> scan strikes `92` through `103`.

Historical model construction intentionally keeps illiquid, wide-spread, low-OI, high-IV, deep ITM/OTM, stale, and otherwise extreme contracts in the candidate bucket so the model learns robustness and failure modes. These observations may score poorly, produce reason codes, or resolve to `no_option_expression`; they must not be removed at acquisition-time solely because they are extreme.

V1 expression coverage remains single-leg only: `long_call`, `long_put`, or `no_option_expression`. Multi-leg spreads remain deferred beyond V1.

## D024B - Promotion classifies artifacts; manager schedules lifecycle; storage executes lifecycle

Date: 2026-05-10
Status: Accepted

Model promotion/evidence scripts may classify artifact retention intent. They may mark promoted model bodies and required lineage as permanent retention and may emit retention hints for regenerable intermediates. They must not call storage cleanup, compression, archive, SQL detach/drop, or deletion executors directly.

The accepted boundary is:

```text
promotion classifies artifacts
manager schedules lifecycle
storage executes lifecycle
```

Lifecycle work caused by promotion must route through manager `storage_lifecycle_request`; `trading-storage` owns protected-set checks, physical lifecycle execution, receipts, and tombstones.

## D025 - Layers 1-8 model-design closeout

Date: 2026-05-07
Status: Superseded by D047

The current `trading-model` model-design phase is closed at Layer 8.

Accepted stack:

```text
MarketRegimeModel
  -> SectorContextModel
  -> TargetStateVectorModel
  -> EventRiskGovernor
  -> AlphaConfidenceModel
  -> PositionProjectionModel
  -> UnderlyingActionModel
  -> OptionExpressionModel
```

Layers 1-8 have accepted contracts, docs, local deterministic scaffolds/evaluation helpers where in scope, registry score naming, and fixture-level verification for the current design phase.

This closeout is superseded by the 2026-05-17 architecture revision that inserts Layer 4 EventFailureRiskModel and makes EventRiskGovernor Layer 9. After Layer 9, downstream work belongs to review / execution-owned boundaries: broker order construction, routing, time-in-force, send/cancel/replace, fills, broker order ids, account mutation, live scheduling, lifecycle retries, and paper/live order placement remain outside this repository.

Remaining work is production hardening and control-plane integration, not new model-layer design: real point-in-time feeds, label calibration, baseline/stability proof, accepted promotion decisions, and exact unified decision-record / artifact contracts through `trading-manager`.

## D026 - Layers 1-9 production promotion requires complete evidence packages

Date: 2026-05-07
Status: Accepted; expanded by D047

Closing the model-design phase does not approve production promotion for any layer.

Every production promotion review for active conceptual Layers 1-9 must use the complete evidence package defined in `docs/95_promotion_readiness.md`: dataset snapshot, chronological split, label refs, eval run, promotion metrics, promotion candidate, thresholds, baseline comparison, split stability, leakage/no-future checks, calibration report, and decision receipt.

Missing evidence or failed gates require a deferred promotion review. Deferred or rejected reviews must not activate configs or move production pointers. Approval can only be considered after the evidence package is complete and gates pass; durable decision and activation belong in `trading-manager`.

## D031 - Promotion closeout records real deferrals before activation

Date: 2026-05-08
Status: Superseded by D036

The useful part of this decision remains: production-promotion closeout must evaluate real evidence and must not activate on missing or failed gates. The implementation detail that `trading-model` persists durable promotion decisions is superseded. `trading-model` now emits model-side evidence/review artifacts; `trading-manager` owns durable review decisions and activation.

## D032 - Layers 3-8 blocked closeout must be agent-reviewed

Date: 2026-05-08
Status: Superseded by D036

Chentong clarified that Layers 3-8 should follow the same promotion principle as Layers 1-2: even when production evaluation substrate is missing, the closeout script must call the reviewer agent. The model-side closeout entrypoint now builds blocked evaluation artifacts and review artifacts only; durable deferred decisions belong in `trading-manager`.

## D033 - Layer 3 production-evaluation substrate is present but not promotable

Date: 2026-05-08
Status: Accepted

A follow-up closeout run created a real Layer 3 production-evaluation substrate instead of leaving Layer 3 only in the generic missing-substrate bucket.

Layer 3 now has PostgreSQL feature rows in `trading_data.feature_03_target_state_vector`, generated model rows in `trading_model.model_03_target_state_vector`, future-target-tradeable-path labels, and reproducible evaluation evidence.

The measured Layer 3 thresholds passed, but promotion remains deferred because Layer 1 and Layer 2 are not production-approved/active upstream dependencies and Layer 3 calibration evidence is still missing. No model-side review artifact may activate a config; activation belongs in `trading-manager`.

`review_target_state_vector_production_substrate.py` is the accepted reproducible entrypoint for rebuilding the Layer 3 substrate and review package. Layers 4-8 remain blocked on missing real production evaluation surfaces and labels; they must not be promoted from the blocked closeout receipts.

## D034 - Layer 1/2 repair fixed stale data completeness but did not justify promotion

Date: 2026-05-08
Status: Accepted

A follow-up Layer 1/2 gate repair found and fixed a stale feature-generation problem before re-reviewing promotion. The repair regenerated `feature_01_market_regime`, `feature_02_sector_context`, `model_01_market_regime`, and `model_02_sector_context` from real PostgreSQL source data instead of lowering thresholds.

Latest Layer 1 evidence fixed the stale row-count and leakage failures. A later scoring repair also excluded `1_coverage_score` and `1_data_quality_score` from predictive-return factor scoring, leaving split-stability passing; promotion still fails baseline improvement, eval-label count, pair-count, and coverage gates.

Latest Layer 2 evidence improved coverage; promotion still fails baseline improvement, selected-vs-blocked lift, and split sign-stability gates.

These results are current negative evidence, not a reason to weaken gates. L1/L2 remain deferred, no activation rows are allowed, and downstream L3 promotion remains blocked on upstream approval plus calibration evidence.

## D035 - Price-action false-breakout evidence stays inside EventRiskGovernor

Date: 2026-05-09
Status: Accepted

False breakouts, failed breakdowns, liquidity sweeps, bull traps, and bear traps are represented as point-in-time `price_action` events consumed by Layer 9 `EventRiskGovernor`.

They are not a new standalone model layer. At inference time they may affect event intensity, direction bias, reversal risk, liquidity-disruption risk, uncertainty, target relevance, and microstructure/symbol impact inside Layer 9 `event_context_vector`. Realized post-event follow-through/failure remains offline label evidence only and must not leak into inference features.

## D037 - Historical training sampling may be broader than live routing

Date: 2026-05-10
Status: Accepted

Historical training dataset construction is allowed to use a broader point-in-time sampling universe than live inference routing. Live routing may narrow candidate flow through upstream model gates, but historical training should not blindly copy those gates when broader sampling is needed to learn robust relationships.

Layer 3 is the critical example: live routing commonly sends targets from Layer 2 selected/prioritized sector baskets, while historical training may include anonymous targets from other sectors, industries, styles, market caps, liquidity tiers, and ETF/stock exposure paths. Each row must still carry point-in-time market and sector context, preserve identity-safety, and avoid future leakage.

Promotion evidence should report both broad historical generalization and live-route simulation performance whenever the training sample universe is wider than the live routed universe.

## D038 - Realtime decision handoff is fixture/shadow routing only

Date: 2026-05-11
Status: Accepted

Realtime execution inputs may enter `trading-model` through `execution_model_decision_input_snapshot` only after `trading-execution` has packaged capture refs into realtime feature/model-input envelopes with historical dataset snapshot refs and frozen model config refs.

`trading-model` accepts `model_realtime_decision_route_plan` as the model-side route plan for fixture/shadow historical-model decision routing. The plan validates Layer 1-8 input coverage and maps each layer to its reviewed generator entrypoint, but it does not run generators, activate production configs, persist durable manager decisions, construct orders, call providers, or mutate accounts.

Production model activation, durable decision records, promotion approval, and execution authority remain manager/execution-owned gates, not implied by this handoff scaffold.

## D039 - Event-risk governor moved after the base trading stack

Accepted: 2026-05-15
Status: Superseded by D047 for the exact layer number

This historical decision moved event intelligence out of the hard upstream alpha path. D047 later inserted EventFailureRiskModel before AlphaConfidenceModel and shifted EventRiskGovernor to Layer 9. The D039 stack at the time was:

1. MarketRegimeModel;
2. SectorContextModel;
3. TargetStateVectorModel;
4. EventFailureRiskModel;
5. AlphaConfidenceModel;
6. PositionProjectionModel;
7. UnderlyingActionModel;
8. TradingGuidanceModel / OptionExpressionModel;
9. EventRiskGovernor / EventIntelligenceOverlay.

Rationale: the base trading path should remain runnable without mature event interpretation, while event intelligence can continue expanding as a high-value side branch. Layer 8 produces the base offline trading-guidance candidate. Layer 9 may intervene after Layer 8 when high-risk point-in-time events are detected.

Allowed event-risk-governor intervention outputs include `block_new_entries`, `max_exposure_factor`, `reduce_exposure_to`, `flatten_position_candidate`, `halt_trading_candidate`, `human_review_required`, event refs, and evidence spans. Under D047 this is Layer 9. It may modify the decision/risk record consumed by execution risk-control, but it must not directly send broker orders or mutate accounts. Flattening/clearing requires high-confidence high-severity evidence and an accepted execution risk policy or human review path.

Physical implementation surfaces now use the current nine-layer names (`model_04_event_failure_risk`, `model_05_alpha_confidence`, `model_06_position_projection`, `model_07_underlying_action`, `model_08_option_expression`, and `model_09_event_risk_governor`). Historical/applied migration records may retain earlier names.

## D040 - Event lifecycle clocks separate scheduled catalysts from surprise events

Accepted: 2026-05-15

Layer 9 event intelligence must preserve event lifecycle timing instead of flattening all evidence into one `event_time`.

Accepted lifecycle classes are `scheduled_known_outcome_later`, `unscheduled_surprise`, `scheduled_recurring_data_release`, `multi_stage_developing_event`, and `unknown`. Required clocks, when known, include awareness, scheduled, published, available, interpretation, resolution, decision/tradeable, and reaction/evaluation windows.

Scheduled-known catalysts such as earnings dates or macro releases may affect pre-event risk because the catalyst shell is visible before the result. Their result facts, beat/miss values, guidance, revisions, and realized market reaction are forbidden until visible through point-in-time release artifacts. Unscheduled surprise events have no specific pre-event event row; only already-visible background vulnerability or hazard priors may exist before the first credible source. Multi-stage events must preserve immutable stage/update refs instead of overwriting the original event.

Training and evaluation must not mix scheduled-known and surprise events under the same label construction unless lifecycle type and phase are explicit features.

## D041 - Abnormal activity must be residual to model-owned market data

Accepted: 2026-05-15

Layer 9 abnormal-activity evidence is not a second copy of bar-derived state. Bars, volume, spread, liquidity, volatility, gap, trend, VWAP distance, and target-state behavior already belong to Layer 1-3 / base guidance inputs when those fields are part of the accepted model stack.

EventRiskGovernor may consume abnormal activity only as trigger/provenance evidence, residual unexplained board/tape disturbance after upstream context conditioning, discrete price-action pattern evidence, or cross-source abnormal evidence not otherwise consumed by the base path. It must not treat every high return/volume/spread z-score as an independent event factor when the same information is already available in upstream context states.

Promotion evidence must prove incremental value over upstream context-state baselines; abnormal-activity-only baselines are diagnostic and cannot justify duplicated bars as event value.

## D042 - Event-activity bridge connects hard news to standardized activity evidence

Accepted: 2026-05-15

Layer 9 may use `event_activity_bridge` to connect raw event evidence to price, liquidity, option, and prediction-market activity. This is the preferred path when a news artifact is difficult to standardize semantically but observable activity provides a stable point-in-time relationship.

Accepted relation types are `pre_event_precursor`, `co_event_reaction`, `post_event_absorption`, `event_activity_divergence`, and `unresolved_latent_hazard`. Accepted explanation statuses are `explained_by_known_event`, `partially_explained`, `unexplained`, `later_explained`, and `review_required`.

A pre-event bridge is latent-event hazard evidence, not proof of the future event. If later news explains earlier activity, training/evaluation may link them with `later_explained`, but the original inference-time bridge remains immutable and point-in-time.

Prediction-market odds are an accepted future activity leg, so this contract can support Polymarket-style event-probability work without making the event layer securities-only.

## D043 - Abnormal activity must prove forward price/path relationship before model-layer promotion

Accepted: 2026-05-15

Before `event_activity_bridge` becomes a separate model layer or risk-intervention input, abnormal activity must prove a stable point-in-time relationship to subsequent price/path outcomes.

The proof must not be a tautology: price-derived abnormality cannot satisfy the gate by correlating with the same price window used to detect it. Required proof levels are `contemporaneous_association`, `forward_price_path_relationship`, `incremental_residual_value`, `cross_market_confirmation_value`, and `out_of_sample_stability`.

Required label families include `forward_return`, `forward_drawdown`, `forward_reversal`, `forward_volatility_expansion`, `forward_gap_or_jump`, and `path_asymmetry` across short and event-relevant horizons such as 5m, 30m, 1h, 1d, 5d, and 20d.

If abnormal activity only describes the current move and does not improve forward labels after controls for market/sector/peer context, target state, ordinary bars/volume/liquidity/volatility, scheduled-event shells, time effects, and regime, it remains descriptive evidence and must not be promoted into a model layer.

## D044 - Activity-price proof must be cross-sectional across size, sector, and event families

Accepted: 2026-05-15

The activity-price proof gate cannot be satisfied by one story stock such as RCAT. The project must run a cross-sectional study across company-size buckets, sector/theme buckets, and event families before promoting `event_activity_bridge` into a separate model layer.

The study must compare all windows, abnormal windows, non-abnormal windows, event-only windows, event+abnormal windows, abnormal-without-visible-event windows, pre-event abnormal windows later explained by event, and event/activity divergence windows.

Acceptance requires forward price/path relationship, incremental residual value after controls, cross-sectional non-story-stock support, out-of-sample stability, leakage controls, and reviewed failure modes. A useful result may be conditional; it does not require every sector or activity class to work.

## D045 - Activity-price proof is direction-neutral first

Accepted: 2026-05-15

The first activity-price proof metric must be direction-neutral. Since downside paths are tradable, abnormal activity should first be evaluated against absolute forward returns, forward path range, max favorable/adverse excursion, tradeable excursion, volatility expansion, absolute gap/jump, and path asymmetry.

Signed average forward return is a secondary diagnostic only. It must not be the primary acceptance metric because positive and negative tradable moves can cancel out and incorrectly make useful abnormal activity look weak.

Directional classification, continuation/reversal inference, and trade expression belong to later model stages after the system proves that abnormal activity expands future price/path opportunity or risk.

## D046 - Activity direction must be tested separately from path expansion

Accepted: 2026-05-15

After direction-neutral tradability is established, abnormal activity must also preserve and test directional orientation. Examples include call-buying or call-sweep surges as bullish evidence, put-buying or put-sweep surges as bearish evidence, positive/negative residual price moves, and high/low liquidity-sweep reversal patterns.

Direction must come from point-in-time activity evidence, not future return labels. Option direction requires side/aggressor context when available because raw call or put volume can be hedging, closing, or inventory flow rather than directional demand.

Directional proof metrics include `activity_direction_bias_score`, `activity_direction_confidence_score`, `signed_directional_forward_return`, `directional_hit_rate`, `opposite_direction_failure_rate`, and `mixed_direction_conflict_score`. Directional proof is a separate gate from absolute path-expansion proof.

## D047 - Layer 4 EventFailureRiskModel inserted before alpha confidence

Accepted: 2026-05-17

The conceptual model stack now inserts `EventFailureRiskModel` at Layer 4 and shifts the later layers forward:

```text
Layer 1: MarketRegimeModel
Layer 2: SectorContextModel
Layer 3: TargetStateVectorModel
Layer 4: EventFailureRiskModel
Layer 5: AlphaConfidenceModel
Layer 6: PositionProjectionModel
Layer 7: UnderlyingActionModel
Layer 8: TradingGuidanceModel / OptionExpressionModel
Layer 9: EventRiskGovernor / EventIntelligenceOverlay
```

Layer 4 contains only agent-accepted, empirically reviewed event/strategy-failure factors. Its output is `event_failure_risk_vector`; it may condition alpha confidence, entry permission, exposure caps, strategy disable pressure, and path-risk amplification, but it must not emit buy/sell/hold, choose expression/contract, size positions, route orders, mutate accounts, or perform destructive SQL/storage actions.

Layer 9 remains the residual event-risk governor and research surface. It may explain residual anomalies, maintain the observation pool, warn/cap/block/review base guidance, and generate event-family promotion packets. A family can move from Layer 9 discovery/observation into Layer 4 only after a script-emitted evidence packet, matched controls/split/leakage/PIT review, incremental value review, and explicit agent/manager acceptance.

This decision is architecture/governance only. Current physical script/package/table names now include `model_04_event_failure_risk`, `model_05_alpha_confidence`, `model_06_position_projection`, `model_07_underlying_action`, `model_08_option_expression`, `model_09_event_risk_governor`, `MODEL_09_*`, and `source_09_event_risk_governor`; historical/applied migrations may retain earlier names.
