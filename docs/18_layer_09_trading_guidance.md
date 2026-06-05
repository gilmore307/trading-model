# M09 - Option Expression / TradingGuidanceModel / OptionExpressionModel

Status: accepted final learned option-expression utility optimizer contract.

`TradingGuidanceModel / OptionExpressionModel` consumes the Layer 8 `underlying_action_plan` / `underlying_action_vector` handoff plus optional point-in-time option-chain context to produce an offline `trading_guidance_record` and, when options are available and allowed, `option_expression_plan` / `expression_vector`.

It is the first layer that may select option expression and contract constraints. It is still not live execution.

Layer 9 must be specified directly in its final learned-model contract form. It must not introduce a temporary learned contract, compatibility bridge, or learned-looking deterministic substitute. A final-contract Layer 9 artifact may move through evidence states such as `defined`, `trained_offline`, `replay_validated`, `shadow_candidate`, `promoted`, or `rejected`; those states are lifecycle evidence, not alternate architecture versions. Only a promoted artifact may affect production decisions.

## Learned Objective

Layer 9 learns constrained option-expression utility for a completed Layer 8 underlying thesis:

```text
U_9(z_t, candidate_option_expression) -> expected_expression_utility
```

`z_t` is the point-in-time Layer 8 thesis, option-surface state, timestamped option-chain candidates, current/pending option exposure, prior-layer market/risk context, and option-expression policy. When `option_surface_status = optionable_chain_available`, `candidate_option_expression` is one of `long_call`, `long_put`, or `underlying_only_expression`. `no_option_expression` is a status/bypass expression for minutes where the option route is unavailable or not applicable; it is not a contract-competing candidate when a usable option universe exists.

When an option universe is available, Layer 9 chooses whether an option is a better expression than direct underlying under liquidity, IV, Greeks, fill, premium-risk, and policy constraints. When the option route is unavailable or not applicable, the row resolves to `no_option_expression` bypass/status evidence instead of scoring fake candidates. It optimizes after-cost expression utility, not alpha discovery, direct-underlying action choice, order routing, sizing, approval, broker mutation, historical action imitation, or hindsight best-contract PnL.

## Training Sample Granularity

Layer 9 training should use dense minute-level option-expression status evidence for every eligible minute where point-in-time Layer 8 thesis context exists. It must not train only on the finally selected contract or only on minutes where an option expression looked attractive. The model needs poor, wide-spread, high-IV, stale, illiquid, unsuitable-DTE, unsuitable-delta, and unavailable-surface cases to learn when the right output is `long_call`, `long_put`, `underlying_only_expression`, or `no_option_expression`.

Layer 9 runtime invocation is conditional on option-surface availability. In live routing, C04 calls M09 only when `option_surface_status = optionable_chain_available` and timestamped option-chain candidates exist. If this minute has no usable option chain, or the underlying is not optionable, C04 bypasses M09 and carries an execution-side bypass/no-option expression without asking M09 to score missing contracts.

Historical training and evaluation may still retain underlying-minute bypass/status rows for missing-chain and non-optionable cases so dataset coverage, labels, and fallback calibration remain explicit. These rows are status/audit evidence, not live M09 inference calls, and they do not produce per-contract candidate rows.

Use separate statuses for the option surface:

```text
optionable_chain_available
optionable_chain_missing
non_optionable_underlying
```

`optionable_chain_available` is the only status that creates per-contract candidate rows for M09 scoring. `optionable_chain_missing` and `non_optionable_underlying` keep only the underlying-minute bypass/status evidence.

`non_optionable_underlying` applies to spot/direct-underlying routes such as BTC where an option-expression surface is outside the accepted route. Such rows may record bypass reason codes for training and audit, but live routing must not call M09 for them.

Contract hard filters, selected-contract thresholds, and expression routes are outputs or downstream policies. They must not be used as default training-row admission filters.

For learned training, the primary row is:

```text
available_time
target_candidate_id
Layer 8 thesis
option surface snapshot/status
candidate option expression
```

When `optionable_chain_available`, the row set must expand across all timestamped contract candidates plus the explicit `underlying_only_expression` alternative. It must include bad candidates: stale quotes, wide spreads, high IV, unsuitable DTE, unsuitable delta, adjusted contracts, low volume, low open interest, unsuitable moneyness, and low fill-quality candidates.

When `optionable_chain_missing` or `non_optionable_underlying`, training keeps minute-level status/bypass rows for calibration and audit but does not create fake contract candidates. These rows resolve to `no_option_expression`; they are not live M09 scoring requests and must not train `underlying_only_expression`.

`underlying_only_expression` and `no_option_expression` are distinct:

- `underlying_only_expression` means the option universe was available, the candidate set was frozen/evaluated, and the best utility is still the direct-underlying expression instead of any option contract.
- `no_option_expression` means there is no usable option route to evaluate, such as a non-optionable underlying, missing chain/snapshot, no listed/orderable candidates, pending option exposure block, or a Layer 8 `maintain` / `no_trade` thesis. It is bypass/status evidence, not proof that evaluated option candidates were worse than the underlying.

## Boundary

Layer 9 owns:

- long-call, long-put, underlying-only-expression, or no-option-expression selection;
- option right, selected contract reference, and contract-fit diagnostics;
- DTE, delta/moneyness, IV, vega/theta, spread/liquidity, fill-quality, and premium-risk constraints;
- side-neutral use of Layer 8 path assumptions: entry price, target/range, stop, holding time, path quality, reversal risk, drawdown risk, and favorable/adverse move estimates;
- offline option-expression labels and promotion evidence.

Layer 9 does **not** own:

- broker order type, route, time-in-force, send/cancel/replace flags, or broker order ids;
- final order quantity, final approval, or account mutation;
- multi-leg spread construction; historical option-expression coverage is single-leg option expression plus non-option fallbacks (`long_call`, `long_put`, `underlying_only_expression`, or `no_option_expression`);
- direct-underlying planned action resolution, which belongs to Layer 8;
- real live/paper routing, which remains in `trading-execution`.

## Inputs

Required point-in-time inputs:

```text
available_time
tradeable_time
target_candidate_id
underlying_action_plan_ref
underlying_action_plan
underlying_action_vector / Layer 8 resolved fields
option_contract_candidates
option_expression_policy
option_surface_status
```

Useful context inputs:

```text
market_context_state
sector_context_state
target_context_state
event_context_vector
position_projection_vector
current option position / premium risk context
pending option exposure / pending option orders
option quote snapshot references
```

Layer 9 must carry the exact quote/snapshot identity used for replay:

```text
option_chain_snapshot_ref
option_quote_available_time
underlying_quote_snapshot_ref
underlying_reference_price
```

Pending option context should be included to avoid duplicate plans:

```text
pending_option_orders
pending_option_premium_exposure
pending_option_fill_probability_estimate
pending_option_cancellable_state
```

Option candidates must be timestamped contract observations. They may include:

```text
contract_ref
option_right / right
expiration
dte / days_to_expiration
strike
moneyness
delta
gamma
theta
vega
iv / implied_volatility
iv_rank
bid_price / bid
ask_price / ask
mid_price / mid
volume
open_interest
contract_multiplier
exercise_style
settlement_type
is_weekly
is_monthly
is_adjusted_contract
last_trade_time
quote_age_seconds
bid_size
ask_size
spread_abs
spread_pct_mid
intrinsic_value
extrinsic_value
breakeven_price
theoretical_value
```

Future realized option returns, target/stop outcomes, and best-contract hindsight are evaluation labels only and must not be present in inference rows.

## Allowed Learned Inputs

Layer 9 learned inputs are point-in-time fields available at or before `available_time`:

- Layer 8 thesis fields: direction, entry assumption, target/range, stop, expected holding period, favorable/adverse move, path quality, reversal risk, drawdown risk, and handoff usefulness context;
- option-surface status and exact replay identities: `option_surface_status`, `option_chain_snapshot_ref`, `option_quote_available_time`, `underlying_quote_snapshot_ref`, and `underlying_reference_price`;
- timestamped option candidate observations: contract ref, right, strike, expiration, DTE, bid/ask/mid, quote age, volume, open interest, bid/ask size, IV/rank, Greeks, intrinsic/extrinsic value, multiplier, exercise style, settlement style, weekly/monthly flag, and adjusted-contract flag;
- prior-layer point-in-time summaries: market, sector, target state, reviewed event context, Layer 6 risk policy, Layer 7 exposure/position projection, and Layer 8 action-plan confidence;
- current and pending option exposure/orders, pending premium exposure, pending fill probability, cancellable state, and premium-risk context;
- option-expression policy constraints such as allowed structures, premium budget, DTE/delta guardrails, spread/liquidity constraints, IV/Greek constraints, and no-option fallback policy.

Layer 9 may consume prior-layer summaries only as upstream state. It must not reconstruct Layer 5 alpha, replace Layer 8 action selection, or override Layer 6/7 risk/exposure policy.

## Forbidden Learned Inputs

Layer 9 learned training and inference must exclude anything that turns it into a hindsight option selector, execution model, action model, or alpha learner:

```text
future option return
future option high / low / close
future option volume / open interest
future IV / Greek change
future spread change
post-decision quote revision
target/stop outcome as input
best-contract hindsight
realized fill outcome
real broker fill price
broker order id
final order quantity
route
time_in_force
order type
execution instruction
future position state
future order state
same-fold Layer 10 discovery
future event attribution
historical selected contract as supervision
raw selected-contract PnL as the only objective
```

Best-contract regret and realized option outcomes are evaluation-only labels. If Layer 9 learns from historical selected contracts as the supervised answer, it becomes a historical option-selector imitator instead of a candidate-expression utility model.

## Outputs

Primary output:

```text
trading_guidance_record / option_expression_plan
```

Vector output:

```text
trading_guidance_vector / expression_vector
```

Resolved fields:

```text
9_resolved_expression_type
9_resolved_option_right
9_resolved_option_surface_status
9_resolved_dominant_horizon
9_resolved_selected_contract_ref
9_resolved_contract_fit_score
9_resolved_expression_confidence_score
9_resolved_no_option_reason_codes
9_resolved_reason_codes
```

Expression types:

```text
long_call
long_put
underlying_only_expression
no_option_expression
```

Option rights:

```text
call
put
none
```

## Score families

Conceptual Layer 9 score families use the `9_` prefix and `<horizon>` suffix for horizon-aware scalar scores.

```text
9_option_expression_eligibility_score_<horizon>
9_option_expression_direction_score_<horizon>
9_option_contract_fit_score_<horizon>
9_option_liquidity_fit_score_<horizon>
9_option_iv_fit_score_<horizon>
9_option_greek_fit_score_<horizon>
9_option_reward_risk_score_<horizon>
9_option_theta_risk_score_<horizon>
9_option_fill_quality_score_<horizon>
9_option_expression_confidence_score_<horizon>
```

Semantics:

- eligibility is high-is-good and means the option expression is admissible under Layer 8 thesis, policy, option-chain, liquidity, IV, and risk constraints;
- direction is signed: positive call-side/bullish or bullish underlying-only expression, negative put-side/bearish or bearish underlying-only expression, near zero no-option expression;
- contract fit is high-is-good and summarizes DTE, delta/Greeks, IV, liquidity, fill quality, and reward/risk;
- theta risk is high-is-bad;
- expression confidence is high-is-good and remains offline model confidence, not order approval.

## Plan payload

`trading_guidance_record / option_expression_plan` may include:

```text
selected_expression_type
selected_option_right
dominant_horizon
selected_contract
option_chain_snapshot_ref
option_quote_available_time
underlying_quote_snapshot_ref
underlying_reference_price
replay_context
contract_constraints
premium_risk_plan
underlying_thesis_ref
underlying_path_assumptions
reason_codes
diagnostics
```

`selected_contract` is a point-in-time contract reference and diagnostics payload. It is null for `underlying_only_expression` and `no_option_expression`. It is not a broker order. `contract_constraints` are model constraints, not routing instructions.

## Deterministic Baseline Generator

The local baseline generator lives in:

```text
src/models/model_09_option_expression/
```

It implements:

- Layer 8 bullish thesis -> long-call candidate search;
- Layer 8 bearish thesis or no-direct-short bearish thesis -> long-put candidate search;
- Layer 8 `maintain` / `no_trade`, pending option exposure, missing option chain, or non-optionable underlying -> `no_option_expression`;
- non-optionable direct-underlying routes such as BTC -> offline bypass/status row with no option-chain scoring and no live M09 invocation;
- option policy blocks or no candidate contract passing hard filters may resolve to `underlying_only_expression` when the Layer 8 thesis still supports a direct-underlying expression;
- reviewed no-provider/no-option database generation from completed Layer 8 rows when the manager gate review finds no Layer 9 training-eligible underlying minutes;
- deterministic selection scoring for right, bid/ask/mid, DTE range, preferred absolute delta range, stale quote age, volume/open interest, spread, adjusted-contract handling, and target-range moneyness guardrails;
- DTE / delta / Greeks / IV / liquidity / reward-risk scoring with per-candidate reason codes;
- offline label join helpers and leakage assertions.

This generator may remain as a schema fixture, deterministic policy baseline, and validation contrast. It must not be promoted as a learned substitute or treated as an intermediate learned architecture.

Fixture tests live in:

```text
tests/test_option_expression_model.py
```

## Option Bucket Policy

Historical model-construction buckets expand from near expirations to farther expirations: current listed week first, then next listed week, then the following listed week, continuing outward only when coverage policy requires it.

For each selected target, the strike bucket is the listed-strike corridor from current underlying reference price to Layer 8 target price plus three listed strike levels below the corridor and three listed strike levels above it. Example:

```text
current_underlying_reference_price = 95
target_price = 100
listed strike spacing = 1
candidate strike bucket = 92 through 103
```

The three-level rule uses actual listed strikes, not a fixed dollar amount. If listed strikes are five-dollar increments, use three listed increments outside the corridor.

Current closed-loop acquisition uses manager request previews for `m09_option_expression_data_acquisition` / `m09_option_expression_data_acquisition` with `max_dte = 45`, `strike_range = 5`, and `option_bucket_policy_ref = LAYER_09_OPTION_BUCKET_STRIKE_POLICY`. The `strike_range = 5` ThetaData bound is the accepted provider-side runtime default for the current bucket loop; model-side selection still applies the target-range moneyness guardrail below.

Historical bucket construction intentionally does not prefilter out illiquid, wide-spread, low-OI, high-IV, deep ITM/OTM, stale, or otherwise extreme contracts. Those observations are useful for robustness and must remain available as features, labels, diagnostics, and reason codes. Selection/evaluation may score them poorly or resolve `underlying_only_expression`, but acquisition-time bucket construction should not hide them from the model.

Expression coverage is single-leg only:

```text
long_call
long_put
underlying_only_expression
no_option_expression
```

`underlying_only_expression` is an explicit fallback when the options layer has an available point-in-time option universe and finds the underlying thesis usable but option contracts are inferior because of policy, liquidity, IV, Greek, DTE, quote freshness, or hard-filter evidence. It keeps selected option contract and option-fit scores empty/zero and records the direct-underlying expression preference for evaluation. It is not an order request.

`no_option_expression` is the explicit status when there is no usable option route to evaluate. It covers missing chain/snapshot evidence, non-optionable underlyings, no listed/orderable candidates, pending option exposure blocks, and Layer 8 `maintain` / `no_trade` theses. It must not be used to label evaluated contracts as merely unattractive.

The accepted expression universe is single-leg long premium plus non-option alternatives. Multi-leg structures are outside this contract unless an accepted expression-policy contract expands the allowed structure set with its own point-in-time candidate construction, utility labels, and validation gates.

## DTE / Delta Scoring Policy

Selection/scoring uses conservative ranges rather than exact DTE points:

```text
10min thesis -> preferred_dte_range = 3-7, no 0DTE
1h thesis -> preferred_dte_range = 7-14
1D thesis -> preferred_dte_range = 7-21
1W thesis -> preferred_dte_range = 21-45
```

Selection/scoring penalizes deep OTM lottery contracts. Preferred absolute delta starts around `0.35-0.65`; learned contract-fit models may adjust this by path quality, expected move, IV, liquidity, and theta pressure.

Layer 8 target/range fields constrain selected-contract scoring when the target range is directionally coherent: bullish call strikes above `target_price_high` and bearish put strikes below `target_price_low` carry `strike_outside_underlying_target_range`. They remain part of bucket evidence, but should not be selected by the baseline selector unless a reviewed exception policy says otherwise.

## Labels and evaluation

Offline label families may include:

```text
realized_option_return_10min
realized_option_return_1h
realized_option_return_1D
realized_option_return_1W
realized_option_max_favorable_excursion_1W
realized_option_max_adverse_excursion_1W
target_premium_hit_before_stop_label_1W
premium_stop_hit_before_target_label_1W
option_spread_adjusted_return_1W
selected_contract_regret_vs_best_candidate_1W
realized_option_mid_return_<horizon>
realized_option_bid_exit_return_<horizon>
realized_option_spread_cost_<horizon>
realized_iv_change_<horizon>
realized_theta_decay_<horizon>
realized_delta_path_exposure_<horizon>
underlying_target_hit_but_option_lost_label_<horizon>
option_no_expression_opportunity_cost_<horizon>
option_expression_avoided_loss_value_<horizon>
candidate_contract_utility_curve_<horizon>
```

Layer 9 labels evaluate expression utility, not selected-contract hindsight. For each candidate expression and horizon, utility should be:

```text
candidate_expression_utility
= realistic_exit_value
  - conservative_entry_cost
  - spread_slippage_penalty
  - commission_fee_penalty
  - quote_staleness_penalty
  - partial_or_unfillable_penalty
  - theta_decay_penalty
  - adverse_iv_change_penalty
  - premium_drawdown_penalty
  - wrong_horizon_penalty
  - churn_or_duplicate_exposure_penalty
  + underlying_only_relative_value
  + no_option_avoided_loss_value
```

Option entry should use a conservative adverse-side fill assumption such as ask-side entry for long premium or a stricter reviewed fill model. Exit should use bid-side or conservative liquidation value. Labels must include spread/slippage, quote age, commissions/fees, partial/unfillable penalties, theta decay, IV crush/expansion, and holding-time consistency. When an option universe exists, labels must compare `long_call`/`long_put` against `underlying_only_expression`, not just rank option contracts. `no_option_expression` labels are calibrated separately from bypass/status rows where no option route was available.

`no_option_expression` can be the correct output when the option surface is absent, no candidate universe can be frozen, pending exposure already exists, or the Layer 8 thesis is `maintain` / `no_trade`. `underlying_only_expression` can be correct when the Layer 8 thesis remains useful but evaluated option contracts are stale, too wide, too expensive, too high theta/IV risk, or otherwise inferior after realistic costs and fills.

## Final Learned Expression Route

Layer 9 learns:

```text
score(PIT_context, candidate_option_expression)
  -> expression utility, risk heads, confidence, explanations
```

Valid model families include:

- pairwise/listwise contract and expression rankers;
- calibrated utility regressors over option-expression candidates;
- multi-head models with utility, fill-quality, no-option, underlying-only, liquidity, IV, Greek, theta, and premium-risk heads;
- constrained expected-utility optimizers over candidate expressions;
- distributional payoff simulation only when point-in-time chain labels are mature and the model still preserves the same expression boundary.

Deterministic hard gates may reject impossible or prohibited structures, missing chains, non-optionable underlyings, stale quotes, blocked policies, or broker/execution fields. They must remain boundary enforcement and candidate filtering, not an alternate scoring route.

## Learned Artifact And Explainability

A promoted or promotion-candidate Layer 9 artifact must include:

- model id, schema version, training window, replay window, fold boundaries, feature schema hash, and lifecycle evidence state;
- training manifest and expression-utility label lineage;
- candidate expression schema and selected expression schema;
- option-chain snapshot lineage and quote/fill realism rule definition;
- trained artifact payload;
- candidate utility scores and top-k candidate comparison;
- selected `option_expression_plan` and `expression_vector`;
- resolved expression type, option right, surface status, dominant horizon, selected contract ref, contract fit, expression confidence, no-option reason codes, and general reason codes;
- candidate count, candidate rejection reasons, selected contract snapshot, and per-component scores for liquidity, IV, Greeks, theta, fill quality, reward/risk, and premium risk;
- replay snapshot refs and pending option exposure context;
- calibration, uncertainty, and feature attribution at context and candidate-expression level;
- PIT, target-leakage, best-contract-hindsight, execution-leakage, fill-realism, no-option, underlying-only, chain-coverage, target-identity, and regime-robustness audits.

Explainability must answer why the selected offline expression is better than other feasible expressions. It must not imply an order type, route, time-in-force, broker instruction, or final quantity.

## Final Contract Implementation Packet

Layer 9 implementation work must target the final contract directly. It may deliver pieces in evidence-gated execution batches, but those batches must not define alternate learned contracts.

The accepted implementation packet contains:

1. **Final contract and boundary**: `TradingGuidanceModel` / `OptionExpressionModel`, `trading_guidance_record`, `option_expression_plan`, `expression_vector`, candidate expression schema, selected expression schema, and forbidden broker/order fields.
2. **Training rows**: dense point-in-time Layer 8 thesis rows expanded across timestamped option-contract candidates plus explicit `underlying_only_expression` alternatives when the option surface is available; separate `no_option_expression` status rows exist only for unavailable/not-applicable option routes.
3. **Candidate construction**: deterministic chain/status expansion for optionable, missing-chain, and non-optionable cases without fake contracts or fake no-option competitors.
4. **Utility labels**: candidate expression utility with conservative fills, spread/slippage, commissions/fees, quote age, partial/unfillable penalties, theta/IV effects, premium drawdown, horizon consistency, no-option avoided loss, and underlying-only relative value.
5. **Learned artifact**: final-contract scorer/ranker for `score(context, candidate_expression) -> utility, risk heads, confidence, explanations`.
6. **Selector**: constrained top-valid-candidate selector under option-surface, policy, liquidity, IV, Greek, fill-quality, premium-risk, and pending-exposure constraints.
7. **Explainability and validation**: candidate utility comparison, rejection reasons, feature attribution, PIT audit, no best-contract hindsight audit, no execution leakage audit, fill-realism audit, no-option/underlying-only calibration, chain coverage, target-identity robustness, and regime robustness.

Evaluation must prove that Layer 9 improves option-expression outcomes versus simpler baselines:

1. no option expression;
2. underlying-only Layer 8 expression;
3. naive ATM nearest-expiration call/put from Layer 8 direction;
4. fixed-delta/fixed-DTE expression;
5. current deterministic contract-fit baseline;
6. final-contract Layer 9 expression-utility model.

Validation must separately check:

- after-cost expression utility versus baselines;
- regret versus the best feasible candidate as evaluation-only evidence;
- calibration by expression-confidence and contract-fit buckets;
- no-option calibration and avoided-loss quality;
- underlying-only fallback calibration;
- fill-realism sensitivity across spread, quote age, liquidity, and bid/ask assumptions;
- spread/liquidity stress, high-IV stress, theta stress, and chain-missing stress;
- horizon stability and churn/duplicate-exposure control;
- target-identity robustness and target-permutation checks;
- chain coverage across DTE, delta, moneyness, IV, liquidity, volume, open interest, and adjusted-contract buckets;
- point-in-time, label-isolation, best-contract-hindsight, execution-leakage, same-fold Layer 10, and future-event leakage audits.

Promotion remains gated until real point-in-time option feeds, realistic fill/cost labels, calibration, leakage controls, baseline improvement, and stability evidence pass review. If Layer 9 cannot beat no-option, underlying-only, naive option, fixed-delta/DTE, and deterministic contract-fit baselines after realistic fills and slippage, the artifact remains unpromoted.

## Invariants

```text
option expression != broker order
contract_ref != broker order id
selected_contract != send order
contract constraints != route / time-in-force
premium risk plan != account mutation
expression confidence != final approval
Layer 9 offline plan != live execution
```

`trading-execution` remains the owner of live/paper broker mutation.
