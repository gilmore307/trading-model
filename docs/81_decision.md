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
| 3 | `TargetStateVectorModel` | `target_state_vector_model` | Direction-neutral target state vector for anonymized target candidates; anonymous candidate construction is Layer 3 preprocessing. |
| 4 | `AlphaConfidenceModel` | `alpha_confidence_model` | Target-state vector to long/short direction confidence, expected value, risk, and uncertainty. |
| 5 | `TradingProjectionModel` | `trading_projection_model` | Confidence plus position/cost/risk context to offline target action and target exposure. |
| 6 | `OptionExpressionModel` | `option_expression_model` | Stock/ETF/long-call/long-put expression and option contract constraints. |
| 7 | `PortfolioRiskModel` | `portfolio_risk_model` | Final offline portfolio risk, sizing, execution-style, exit, and kill-switch gate. |

Event evidence remains an overlay/input to target-state, confidence, projection, expression, and risk work. Live/paper order placement remains outside this repository and no layer should be renamed `ExecutionModel`.

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
  -> target_state_vector

AlphaConfidenceModel
  -> alpha_confidence_state

TradingProjectionModel
  -> trading_projection_state

OptionExpressionModel
  -> expression_state

Event evidence overlay
  -> event/risk inputs to Layer 3+ and portfolio risk

PortfolioRiskModel
  -> portfolio_risk_state / final offline risk gate
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

`MarketRegimeModel` V1 outputs a continuous point-in-time broad market-property vector keyed by `available_time`.

The physical output table is:

```text
trading_model.model_01_market_regime
```

The downstream conceptual view is:

```text
market_context_state
```

Current model-facing factor keys:

```text
1_price_behavior_factor
1_trend_certainty_factor
1_capital_flow_factor
1_sentiment_factor
1_valuation_pressure_factor
1_fundamental_strength_factor
1_macro_environment_factor
1_market_structure_factor
1_risk_stress_factor
1_transition_pressure
1_data_quality_score
```

Docs, model-facing payloads, and physical SQL columns use the same compact `1_*` contract. SQL writers quote numeric-leading identifiers where required instead of creating `layer01_*` aliases.

Layer 1 must not output sector rankings, ETF rankings, stock candidates, strategy labels, or pre-assigned ETF/sector behavior classes.

ETF/sector labels such as `growth`, `defensive`, `cyclical`, `inflation_sensitive`, or `safe_haven` are not Layer 1 facts. If useful, they are Layer 2 posterior interpretations inferred from point-in-time behavior, holdings, and market-state-conditioned trend stability.

## D005 - Layer 1 evidence and evaluation maturation

Date: 2026-05-02
Status: Accepted

Layer 1 structure is settled for V1. Remaining Layer 1 work is evidence and evaluation maturation, not boundary redesign.

For each market-property factor, maintain `src/models/model_01_market_regime/evidence_map.md` as the feature-to-factor evidence map classifying feature families as:

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
- usefulness for `PortfolioRiskModel` risk, sizing, execution-style, exit, and kill-switch policy.

A `market_context_state` alias/view may wrap the current factor columns for downstream readability without changing the core physical fields.

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

## D010 - Model governance and promotion evidence stay model-local until accepted

Date: 2026-05-01
Status: Accepted

Model evaluation, config versions, promotion candidates, promotion decisions, rollback proposals, and active-pointer proposals are model-governance artifacts.

Current implementation provides dry-run/evidence-building paths first, plus an explicit durable persistence path for reviewed promotion decisions. `review_market_regime_promotion.py --write-decision` persists evaluation artifacts when supplied, config/candidate rows, and the promotion decision. `--activate-approved-config` activates only accepted approval decisions by inserting a `model_promotion_activation` event, marking the reviewed `model_config_version` row `active`, and retiring prior active configs for the same model. Deferred or rejected decisions must never change the active config.

The current table-name terms are registered in `trading-manager`; concrete column-level registration can wait until real evaluation/promotion flows prove the schema.

## D011 - Model output keys carry layer ownership prefixes

Date: 2026-05-02
Status: Accepted

Model-facing output vectors and output fields must carry their layer owner in the field name so downstream contracts cannot confuse similarly named concepts across layers.

Rules:

- Layer 1 model-facing output keys use compact `1_*` names, for example `1_trend_certainty_factor`.
- Layer 2 model-facing output keys use compact `2_*` names, for example `2_sector_conditional_behavior_vector` and `2_trend_stability_score`.
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

Layer 4/5 consumers own direction-confidence calibration, target/stop/action projection, position sizing, and final trading instructions. Layer 3 remains a state-vector model.

## D018 - Vector taxonomy and Layer 3 preprocessing boundary

Date: 2026-05-05
Status: Accepted

The V2.2 three-layer tradability design uses a strict vocabulary split:

- `feature_*` surfaces are deterministic point-in-time inputs owned by `trading-data`.
- `*_feature_vector` values are model-facing input vectors.
- `*_state` values are narrow current-state model outputs.
- `*_state_vector` is reserved for an accepted block-structured state output such as Layer 3 `target_state_vector`.
- `*_score` fields are scalar dimensions and must not silently combine direction, quality, tradability, confidence, and position size.
- `*_diagnostics` and `*_explainability` are support surfaces unless promoted separately.
- `*_label` / `*_outcome` values are training/evaluation-only and must never enter inference vectors.

Anonymous target candidate construction is Layer 3 preprocessing and sample organization. It is not a separate model, not a fourth layer, not Layer 2.5, and not a peer to `TargetStateVectorModel`.

`anonymous_target_feature_vector` is the Layer 3 model-facing input vector produced by preprocessing. `target_state_vector` is the Layer 3 model output. Audit/routing metadata, including real symbol references, remains outside model-facing vectors.

Layer 1 should migrate toward V2.2 market-tradability semantics: market direction, direction strength, trend quality, stability, risk stress, transition risk, breadth participation, correlation/crowding, dispersion opportunity, liquidity pressure/support, coverage, and data quality. Current `1_*_factor` fields remain implementation compatibility fields until a reviewed code/SQL migration replaces them.
