# M04 - Event Failure Risk / EventFailureRiskModel

Status: accepted Layer 4 contract and physical scaffold.

## Purpose

`EventFailureRiskModel` converts **agent-reviewed, empirically accepted event/strategy-failure relationships** into a point-in-time `event_failure_risk_vector` before alpha confidence is estimated. Agent review must use the fixed `event-strategy-promotion-review` skill.

This layer exists because some event families do not need to be standalone directional alpha to matter. If reviewed evidence shows that a family reliably causes strategy failure, invalidates entry assumptions, worsens path risk, creates overnight/weekend/holiday session-gap risk, or breaks a strategy family under specific market/sector/target contexts, that evidence should condition the decision stack before alpha, position, action, or expression planning.

## Placement

```text
Layer 1: MarketRegimeModel
  -> Layer 2: SectorContextModel
  -> Layer 3: TargetStateVectorModel
  -> Layer 4: EventFailureRiskModel
  -> Layer 5: AlphaConfidenceModel
  -> Layer 6: DynamicRiskPolicyModel
  -> Layer 7: PositionProjectionModel
  -> Layer 8: UnderlyingActionModel
  -> Layer 9: TradingGuidanceModel / OptionExpressionModel
  -> Layer 10: EventRiskGovernor / EventIntelligenceOverlay
```

Layer 4 is not broad event alpha and not raw-news ingestion. It is a narrow pre-alpha failure-risk gate for event families that have already passed agent review.

## Quantitative role

Layer 4 is the **quantitative event-failure-risk model**. Layer 10 and review decide whether an event family/impact relationship is real enough to supervise; Layer 4 learns how large that accepted relationship is for the current point-in-time event, market state, sector state, target state, strategy family, and horizon.

Layer 4 answers:

- How applicable is this reviewed event-failure relationship to the current target/context?
- How severe is the strategy-failure risk for each horizon?
- How much should entry-block, exposure-cap, strategy-disable, path-risk, session-gap, confidence, and tradability pressure increase?
- How strong is the evidence quality for the current event observation?

Layer 4 must not decide whether a new event family is real, discover raw event causes, classify co-event dominance, or decide that a source/document type is globally important. Those are Layer 10/review responsibilities.

## Inputs

Required inputs are point-in-time and review-gated:

- `market_context_state` / `market_context_state_ref`;
- `sector_context_state` / `sector_context_state_ref`;
- `target_context_state` / `target_context_state_ref`;
- accepted `event_strategy_failure_gate` or equivalent reviewed promotion record;
- point-in-time event observation rows for only the reviewed event family;
- strategy-family applicability metadata;
- evidence-packet reference and agent-review decision.

The event observation row is the direct event-facing input to Layer 4. It must already contain the inference-time scope facts Layer 4 is allowed to use:

- `event_id` / `canonical_event_id`;
- `available_time`;
- `event_family` / `normalized_event_type`;
- `expected_impact_scope`;
- `affected_scope`;
- `affected_entities`;
- `scope_confidence_score`;
- `scope_support_evidence_ref`;
- `review_status`.

Layer 4 must not infer impact scope directly from raw news, SEC text, macro pages, transcripts, or provider payloads. Raw artifacts are standardized upstream into point-in-time event observations; Layer 4 then combines those observations with Layer 1/2/3 state to decide risk conditioning for the current target.

Layer 4 must not consume arbitrary raw news, unreviewed event-family screening rows, post-hoc residual-discovery candidates, future returns, broker outcomes, or unapproved event-family associations.

## Event pools

Calendar, market-structure dates, and persistent event regimes start in the global event observation pool, not in Layer 4 training. The first required system capability is point-in-time observation coverage that knows key dates, active periods, and availability clocks:

- ordinary overnight and Friday/weekend windows;
- market holidays, long weekends, early closes, and pre-holiday sessions;
- Thanksgiving, Christmas, and other major long closures;
- triple-witching and major option-expiry windows;
- index reconstitution and Nasdaq-100 rebalance windows;
- halt or other scheduled/announced non-continuous-market windows when available.
- persistent special-period regimes such as pandemic risk, tariff-war periods, geopolitical war/escalation periods, banking-system stress, sanctions regimes, or policy crisis windows.

These rows are observation-only until Layer 10 sees failures or residual anomalies around them and links the failure to a candidate event family/mechanism after basic controls. At that point the family can enter the `focused_event_pool` / `watched_event_pool`: a candidate pool for systematic data collection, offline Layer 4 candidate training, and Layer 5 validation. This is not production acceptance.

The production route has three separate pools:

- `global_event_observation_pool`: point-in-time event/date/regime facts with no causal claim.
- `focused_event_pool` / `watched_event_pool`: Layer 10-selected candidate families that deserve systematic data extraction, candidate Layer 4 training, and Layer 5 validation.
- `accepted_layer4_event_family`: event families/mechanisms that passed Layer 4 candidate training, Layer 5 validation, and Layer 10/review disposition for future production conditioning.

Layer 4 may train candidate models from focused-pool observations, but production Layer 4 conditioning may use only `accepted_layer4_event_family` rules or accepted `event_strategy_failure_gate` packets.

Persistent regimes are interval observations rather than single headlines. They may remain active or shadow-active even when no fresh article appears. Their point-in-time rows should preserve regime start, current status, last material update, decay/staleness rule, scope, and evidence refs. Layer 4 may use them for candidate training after Layer 10 places the family in the focused pool, but production use still requires acceptance after Layer 5 validation and Layer 10/review disposition.

`trading-data/docs/23_event_source_registry.md` owns how historical and realtime/future event observations are acquired. Layer 4 relies on the resulting point-in-time event observations and must not choose raw source priority itself.

## Event partitions

Layer 4 event evidence is partitioned by **impact scope**, not by data source or article/source type. SEC filings, earnings releases, company news, macro releases, sector news, and political events can each be local or broad depending on their point-in-time expected and reviewed impact.

The required partitions are:

- global/common impact context: reviewed events whose expected impact is reusable across the market, a broad sector, an industry, a theme factor, supply-chain peers, index constituents, or other multi-target scope;
- target-local impact context: reviewed events whose expected impact is limited to the specific symbol, issuer, target candidate, or same-symbol instrument set for the current fold.

Both partitions must preserve point-in-time clocks, reviewed family identity, impact scope, provenance, and evidence references. Model fitting may join both partitions for a target/fold, but the partitions must remain physically and logically separable so retention and replay cannot confuse reusable global impact context with fold-local target evidence.

Layer 4 must distinguish impact scope known at inference time from scope learned after the market response:

- `expected_impact_scope`: point-in-time interpretation using only evidence available at `available_time`, accepted prior event-family rules, issuer/sector/index/peer/supply-chain metadata, source materiality, and reviewed scope priors;
- `realized_impact_scope_label`: evaluation-only label from later market/sector/peer/target reaction windows, used for review, calibration, and future-fold promotion only.

`expected_impact_scope` must be resolved by comparing the interpreted event against the current state stack:

- Layer 1 `market_context_state`: broad regime, stress, liquidity, breadth, dispersion, correlation/crowding, and transition-risk context;
- Layer 2 `sector_context_state`: affected sector/industry/theme/peer behavior, trend stability, relative strength, correlation, and sector tradability context;
- Layer 3 `target_context_state`: target-specific liquidity, path/tradability, residual behavior, state-transition quality, and target-vs-sector/market alignment.

The scope resolver should produce auditable support for each candidate scope: market/global, sector/industry/theme, peer/supply-chain/index basket, and target-local. If event evidence is strong but state-stack support is weak or contradictory, the scope should remain narrow or review-required instead of being promoted to global/common impact.

For example, a large issuer earnings event can be target-local when reviewed evidence only supports issuer-specific impact, or global/common when point-in-time rules support broad market, index, sector, AI/theme, supplier/customer, or volatility/risk-appetite impact. The later fact that the whole market moved cannot be used as an inference-time scope fact for the same fold.

## Fold cleanup boundary

Historical-training folds may delete fold-local target event working data after the fold is accepted or abandoned. This cleanup applies only to target event rows/artifacts/materialized joins that were created for that specific fold.

Fold cleanup must not delete global/common impact context, reviewed global event evidence packets, shared event-family acceptance artifacts, or any cross-target reusable event references. If a fold consumes global/common impact events, it should record fold-local references to those global rows rather than copying them into a deletable target-event namespace.

## Output

Primary output: `event_failure_risk_vector`.

Recommended score families:

| Score family | Direction | Meaning |
| --- | --- | --- |
| `4_event_strategy_failure_risk_score_<horizon>` | high is bad | Probability/severity that the reviewed event family invalidates the relevant strategy setup. |
| `4_event_entry_block_pressure_score_<horizon>` | high is blockier | Pressure to block new entries for affected strategy families. |
| `4_event_exposure_cap_pressure_score_<horizon>` | high is more restrictive | Pressure to cap exposure before position projection. |
| `4_event_strategy_disable_pressure_score_<horizon>` | high is more restrictive | Pressure to disable or downweight a specific strategy family temporarily. |
| `4_event_path_risk_amplifier_score_<horizon>` | high is bad | Event-driven amplification of adverse path/gap/volatility risk. |
| `4_event_session_gap_risk_score_<horizon>` | high is bad | Scheduled calendar / market-structure event risk around overnight, weekend, holiday, expiry, rebalance, halt, or other non-continuous-market windows. |
| `4_event_evidence_quality_score_<horizon>` | high is good | Quality of the reviewed evidence and PIT match. |
| `4_event_applicability_confidence_score_<horizon>` | high is good | Confidence that the reviewed event family applies to this target/context/strategy. |

Allowed resolved statuses:

- `no_reviewed_event_failure_risk`;
- `observe_only`;
- `alpha_conditioning_required`;
- `entry_block_recommended`;
- `exposure_cap_recommended`;
- `strategy_family_disable_recommended`;
- `human_review_required`.

## Downstream use

Layer 5 `AlphaConfidenceModel` consumes `event_failure_risk_vector` as a **conditioning input**. It may lower confidence, increase path/drawdown risk, reduce alpha tradability, or mark alpha as review-required. It must keep the base no-event alpha and event-conditioned alpha auditable.

Layer 6-8 may consume the resolved Layer 4 conditioning indirectly through Layer 5/6 handoffs. They must not independently re-promote raw event evidence. Trading-calendar and market-structure dates are scheduled event families for Layer 4 when they create risk through market participant behavior or forced calendar mechanics.

Layer 4 may score `4_event_session_gap_risk_score_<horizon>` for reviewed calendar/structure events such as ordinary overnight, Friday/weekend de-risking, holiday and long-weekend closures, early closes, Thanksgiving/Christmas closures, triple-witching, major option-expiry windows, index reconstitution, Nasdaq-100 rebalance, and other scheduled market-structure dates. The point is not the data source; it is that the calendar date itself can change behavior before, during, or after the closed/rebalance/expiry window.

Layer 6 consumes the resulting risk pressure when setting budgets. It should not independently infer raw calendar-event risk or reinterpret market-structure dates outside the Layer 4 event gate.

Layer 10 remains responsible for residual discovery, unexplained anomaly review, observation-pool maintenance, and proposing future event-family promotions into Layer 4.

## Promotion gate into Layer 4

An event family can enter Layer 4 only after all of the following are true:

1. family-specific association or residual-failure evidence exists from Layer 10 post-failure attribution;
2. matched controls, split stability, leakage checks, and point-in-time clocks are reviewed;
3. the effect is strategy-failure relevant, not merely descriptive news coincidence;
4. the family has an emitted evidence packet;
5. agent review through `event-strategy-promotion-review` explicitly accepts `accept_layer_04_event_failure_risk_scope` or equivalent;
6. manager registry records the accepted scope and allowed decision effects.

Absent this reviewed promotion, the family remains in Layer 10 research/observation/governance only.

## Supervision and retraining loop

Layer 4 is not an unsupervised event-discovery model. It is review-supervised by Layer 10 attribution evidence.

Layer 10 supplies a reviewed supervision packet or training contract, not model weights or same-fold hindsight facts. The accepted packet should define:

- `event_family_key` and mechanism;
- expected impact-scope rule and affected scopes/entities;
- applicable market, sector, target, and strategy-family states;
- horizons where the relationship may apply;
- positive failure sample definition;
- negative and matched-control design;
- co-event/confounder handling;
- leakage rules;
- minimum evidence and stability thresholds;
- allowed Layer 4 effects.

Layer 4 then trains or updates the quantitative `event_failure_risk_vector` model from point-in-time event observations, Layer 1/2/3 state, strategy context, and reviewed failure labels. If later Layer 5/6/7/8/9 evaluation shows that a Layer 4 event family has no incremental value, overblocks valid alpha, or is explained by a dominant co-event, Layer 10 must revise, demote, split, or reject the supervision packet before any future Layer 4 retraining. The changed supervision can affect only later folds.

## Hard boundaries

`EventFailureRiskModel` must not:

- emit buy/sell/hold;
- emit standalone directional event alpha;
- choose position size or target exposure;
- choose option contracts, strikes, DTE, delta, order type, or route;
- mutate broker/account state;
- start realtime services;
- physically delete artifacts or run destructive SQL;
- promote event families automatically from local screens.
