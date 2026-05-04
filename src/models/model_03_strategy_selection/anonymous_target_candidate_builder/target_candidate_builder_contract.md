# anonymous target candidate builder V1 contract

This file owns the first model-local contract for the boundary between
`sector_context_state` and `StrategySelectionModel` target-aware fitting.

The builder is part of Layer 3, not a separate model layer. It is the point-in-time preparation
sub-boundary that expands selected sector/industry baskets into anonymous target
candidate rows while preserving real symbol references only for audit and
routing.

## Purpose

The anonymous target candidate builder answers:

> Given Layer 2 selected/prioritized sector or industry baskets, which target
> candidates can be evaluated by Layer 3 without exposing ticker/company
> identity to model fitting?

It may create stock or ETF target candidates, but it does not choose a final
trade, strategy family, entry timing, option contract, size, or portfolio
allocation.

## Row identity

Conceptual row shape:

```text
anonymous_target_candidate[available_time, target_candidate_id]
```

Required model-facing identity fields:

| Field | Type | Role |
|---|---|---|
| `available_time` | timestamp | Point-in-time availability of the candidate row. |
| `target_candidate_id` | text | Opaque row key for model-facing target work. It is a key, not a fitting feature. |
| `candidate_builder_version` | text | Version/config label that produced the candidate row. |
| `market_context_state_ref` | text/null | Reference to the Layer 1 market-context row used as context. |
| `sector_context_state_ref` | text/null | Reference to the Layer 2 sector-context row that admitted or prioritized the candidate. |

`target_candidate_id` must not reveal raw ticker, company, exchange, issuer, or
stable symbol identity. It may be deterministic inside a reviewed artifact/run,
but Layer 3 must not use it as a categorical feature, and long-lived ids must
not become a route for memorizing symbol-specific winners.

## Metadata separation

The builder produces two separate surfaces:

```text
model-facing:
  available_time
  target_candidate_id
  anonymous_target_feature_vector
  market_context_state_ref
  sector_context_state_ref

metadata / audit / routing:
  audit_symbol_ref
  routing_symbol_ref
  source_sector_or_industry_symbol
  source_holding_ref
  source_stock_etf_exposure_ref
  symbol_resolution_version
```

Metadata may contain real symbols because downstream execution and audit need to
know what the candidate maps to. Metadata must not be joined into model-facing
fitting vectors except through reviewed non-identity evidence fields.

## Eligible inputs

All inputs must be available at or before `available_time`.

Allowed inputs:

- selected, watched, or prioritized Layer 2 `sector_context_state` rows;
- Layer 1 `market_context_state` references and factor values as context;
- ETF holdings snapshots and `stock_etf_exposure` evidence for transmitting
  selected sector/industry baskets into stock candidates;
- target-local point-in-time price, trend, volatility, liquidity, spread, gap,
  borrow/shortability, optionability, abnormal-activity, and event-risk evidence;
- provider/source quality and freshness diagnostics as quality evidence;
- strategy-library eligibility facts that do not encode historical symbol wins.

Disallowed inputs:

- raw ticker or company identity as model-facing features;
- memorized symbol-specific winner/loser labels;
- future returns or realized PnL as production fields;
- post-event explanations unavailable at `available_time`;
- final strategy, option-contract, size, or portfolio decisions.

## Candidate generation flow

V1 flow:

```text
sector_context_state selected/watch baskets
  -> ETF holdings / stock_etf_exposure transmission
  -> target-local evidence join at available_time
  -> eligibility and duplicate-collapse rules
  -> anonymous_target_feature_vector assembly
  -> anonymity/leakage checks
  -> StrategySelectionModel input rows
```

Layer 2 may admit or prioritize baskets. The builder expands those baskets into
target candidates. Strategy-aware final target selection starts only after Layer
3 evaluates anonymous target candidates.

## Model-facing feature vector blocks

The V1 `anonymous_target_feature_vector` should be structured as blocks rather
than one opaque scalar.

| Block | Meaning |
|---|---|
| `target_behavior_vector` | Target-local price/trend/momentum/reversal/chop/volatility shape. |
| `target_liquidity_tradability_vector` | Volume, spread, capacity, borrow/shortability, optionability, and slippage diagnostics. |
| `sector_context_projection_vector` | Layer 2 sector/industry context values projected onto the candidate without exposing ticker identity. |
| `market_context_projection_vector` | Layer 1 broad market context values relevant to target and strategy fitting. |
| `exposure_transmission_vector` | Holdings/exposure-derived strength, concentration, and confidence after selected basket transmission. |
| `event_risk_context_vector` | Scheduled/breaking event density, abnormal activity, gap/jump risk, and source-priority context. |
| `cost_and_constraint_vector` | Cost, tradability, data constraints, option-chain availability, and no-trade diagnostics. |
| `candidate_quality_vector` | Coverage, freshness, evidence count, duplicate-collapse confidence, and anonymity-check results. |

These block names are model-local until implementation/evaluation proves which
fields should be promoted through `trading-manager`.

## Eligibility and handoff fields

Recommended V1 fields:

| Field | Type | Role |
|---|---|---|
| `candidate_eligibility_state` | text | One of `eligible`, `watch`, `excluded`, or `insufficient_data` unless a registered status vocabulary supersedes it. |
| `candidate_eligibility_reason_codes` | text/null | Semicolon-separated stable reason codes. |
| `candidate_source_rank` | integer/null | Rank inherited from sector/basket transmission or target evidence; not a portfolio weight. |
| `candidate_generation_reason_codes` | text/null | Why this candidate was generated. |
| `candidate_data_quality_score` | float/null | Coverage/freshness/reliability summary. |
| `candidate_anonymity_check_state` | text | Pass/fail/watch state for identity-leakage checks. |

If these fields become shared cross-repository contracts, route them through
`trading-manager` before downstream repositories depend on them.

## Excluded V1 outputs

The builder must not output:

- final selected stock symbols as model-facing fields;
- company names, ticker strings, CIKs, FIGIs, ISINs, or exchange-specific identity fields in the fitting vector;
- strategy family choice or strategy parameters;
- entry time, entry price, stop, target, or holding-period instruction;
- option contract, DTE, delta, strike, premium, or Greeks selection;
- portfolio size, exposure, execution policy, or kill-switch instruction;
- future returns, realized PnL, or post-decision execution outcomes.

## Evaluation requirements

V1 acceptance must show:

1. every candidate row is point-in-time and keyed by evidence available at or before `available_time`;
2. Layer 2 selected/prioritized baskets are the source of sector transmission;
3. ETF holdings and `stock_etf_exposure` are used only at this candidate-builder boundary, not as Layer 2 core behavior inputs;
4. model-facing vectors exclude raw ticker/company identity and direct symbol-derived categorical features;
5. audit/routing metadata can recover the real symbol without being joined into fitting vectors;
6. duplicate candidates from multiple sector/industry baskets collapse or remain multi-source with explicit reason codes;
7. generated candidates improve downstream StrategySelectionModel evaluation versus a sector-only or market-only baseline;
8. anonymity checks catch accidental identity leakage before promotion.
