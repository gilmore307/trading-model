# Layer 04 — EventFailureRiskModel

Status: accepted architecture revision and current physical Layer 4 scaffold. Conceptual Layer 4 is inserted ahead of alpha confidence; active non-historical packages/scripts/registry rows now use the Layer 4 surface, while historical/applied migration records remain unchanged.

## Purpose

`EventFailureRiskModel` converts **agent-reviewed, empirically accepted event/strategy-failure relationships** into a point-in-time `event_failure_risk_vector` before alpha confidence is estimated.

This layer exists because some event families do not need to be standalone directional alpha to matter. If reviewed evidence shows that a family reliably causes strategy failure, invalidates entry assumptions, worsens path risk, or breaks a strategy family under specific market/sector/target contexts, that evidence should condition the decision stack before alpha, position, action, or expression planning.

## Placement

```text
Layer 1: MarketRegimeModel
  -> Layer 2: SectorContextModel
  -> Layer 3: TargetStateVectorModel
  -> Layer 4: EventFailureRiskModel
  -> Layer 5: AlphaConfidenceModel
  -> Layer 6: PositionProjectionModel
  -> Layer 7: UnderlyingActionModel
  -> Layer 8: TradingGuidanceModel / OptionExpressionModel
  -> Layer 9: EventRiskGovernor / EventIntelligenceOverlay
```

Layer 4 is not broad event alpha and not raw-news ingestion. It is a narrow pre-alpha failure-risk gate for event families that have already passed agent review.

## Inputs

Required inputs are point-in-time and review-gated:

- `market_context_state` / `market_context_state_ref`;
- `sector_context_state` / `sector_context_state_ref`;
- `target_context_state` / `target_context_state_ref`;
- accepted `event_strategy_failure_gate_v1` or equivalent reviewed promotion record;
- point-in-time event identity/scope/evidence rows for only the reviewed event family;
- strategy-family applicability metadata;
- evidence-packet reference and agent-review decision.

Layer 4 must not consume arbitrary raw news, unreviewed event-family screening rows, post-hoc residual-discovery candidates, future returns, broker outcomes, or unapproved event-family associations.

## Output

Primary output: `event_failure_risk_vector`.

Recommended V1 score families:

| Score family | Direction | Meaning |
| --- | --- | --- |
| `4_event_strategy_failure_risk_score_<horizon>` | high is bad | Probability/severity that the reviewed event family invalidates the relevant strategy setup. |
| `4_event_entry_block_pressure_score_<horizon>` | high is blockier | Pressure to block new entries for affected strategy families. |
| `4_event_exposure_cap_pressure_score_<horizon>` | high is more restrictive | Pressure to cap exposure before position projection. |
| `4_event_strategy_disable_pressure_score_<horizon>` | high is more restrictive | Pressure to disable or downweight a specific strategy family temporarily. |
| `4_event_path_risk_amplifier_score_<horizon>` | high is bad | Event-driven amplification of adverse path/gap/volatility risk. |
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

Layer 6-8 may consume the resolved Layer 4 conditioning indirectly through Layer 5/6 handoffs. They must not independently re-promote raw event evidence.

Layer 9 remains responsible for residual discovery, unexplained anomaly review, observation-pool maintenance, and proposing future event-family promotions into Layer 4.

## Promotion gate into Layer 4

An event family can enter Layer 4 only after all of the following are true:

1. family-specific association or residual-failure evidence exists;
2. matched controls, split stability, leakage checks, and point-in-time clocks are reviewed;
3. the effect is strategy-failure relevant, not merely descriptive news coincidence;
4. the family has an emitted evidence packet;
5. agent review explicitly accepts `accept_layer_04_event_failure_risk_scope` or equivalent;
6. manager registry records the accepted scope and allowed decision effects.

Absent this reviewed promotion, the family remains in Layer 9 research/observation/governance only.

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
