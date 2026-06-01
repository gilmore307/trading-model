# M06 - Dynamic Risk Policy / DynamicRiskPolicyModel

Status: accepted final learned contract for Layer 6 as a portfolio risk-policy optimizer.

## Purpose

DynamicRiskPolicyModel converts minute-level whole-market state, systemic event pressure, and replayed portfolio/account capacity into dynamic_risk_policy_state. Alpha quality is an optional conditioning input when the row is tied to a candidate or active position.

It is a model-internal policy state, not an execution hard-limit gate. Hard order boundaries, account kill switches, and broker permission remain execution/order-gate responsibilities.

Layer 6 must be specified directly in its final learned-model contract form. It must not introduce a temporary learned contract, compatibility bridge, or learned-looking deterministic substitute. A final-contract Layer 6 artifact may move through evidence states such as `defined`, `trained_offline`, `replay_validated`, `shadow_candidate`, `promoted`, or `rejected`; those states are lifecycle evidence, not alternate architecture versions. Only a promoted artifact may affect production decisions.

## Learned Objective

Layer 6 learns a constrained portfolio risk policy. For each point-in-time row it estimates the portfolio utility of allowed risk-policy buckets and emits risk-budget, premium-budget, new-exposure permission, systemic haircut, portfolio-capacity, policy-stability, and policy-confidence scores.

The optimization target is:

```text
portfolio_utility(policy) - portfolio_utility(deterministic_baseline)
```

The utility is risk-adjusted portfolio utility, not single-target return, trade PnL, direction accuracy, alpha rank, or final action profitability. It should reward stable use of risk budget and penalize drawdown, tail loss, concentration, budget breach, turnover, and hard-rule violations.

## Inputs

- Layer 1 market_context_state
- broad/systemic event-risk state
- Layer 5 alpha_confidence_vector when the row is candidate- or position-conditioned
- replayed portfolio exposure state
- replayed account capacity state

The layer is primarily global-market driven. Sector or target-specific evidence can cap, skip, or haircut the current target, but must not define the global risk budget.

## Training Sample Granularity

Layer 6 training must use minute-level continuous risk-policy rows. Live runtime components may trigger Layer 6 on demand, but training should still include every eligible market minute so the model learns the risk-policy state during both action and no-action periods.

Layer 6 has three accepted row scopes:

- `global`: one portfolio/account policy row per eligible minute, independent of any specific target candidate.
- `target_candidate`: a candidate-conditioned policy row when Layer 5 has produced an alpha candidate for the minute.
- `active_position`: a position-conditioned policy row when an existing position needs minute-level add/reduce/hold context for Layer 7.

The base training table is not `minute x all symbols`. It is a minute-level global policy table plus target/position-conditioned rows where a candidate or active position exists. This keeps Layer 6 trained on every minute of risk context without pretending every symbol has a budget decision every minute.

The `global` row learns the background budget posture: risk-on/risk-off, premium budget pressure, market stress haircut, systemic event haircut, portfolio capacity, policy stability, and policy confidence. Candidate and active-position rows inherit that context and add Layer 5 alpha quality or position context for downstream Layer 7.

`target_candidate` and `active_position` rows must not rewrite the global policy envelope. They can only learn local permission, haircut, budget consumption, or capacity fit inside the current global risk-policy state.

## Allowed Learned Inputs

All learned inputs must be available at the row `available_time` and carry auditable point-in-time lineage.

- whole-market minute state: market regime, broad trend, volatility, liquidity, breadth, dispersion, correlation, market stress, and risk appetite;
- systemic event pressure: reviewed broad macro, policy, geopolitical, regulatory, liquidity, credit, market-structure, or financial-system pressure;
- replayed portfolio/account state: cash, buying-power/capacity proxy, used risk budget, used premium budget, gross/net exposure, concentration, correlation crowding, drawdown, day PnL state, unrealized PnL state, and open-risk pressure;
- Layer 5 alpha quality summary for candidate- or position-conditioned rows, limited to calibrated quality, confidence, path-risk, tradability, and distribution summaries;
- candidate or active-position context: liquidity, volatility, spread/cost pressure, sector/industry correlation, event pressure, optionability status, estimated risk consumption, and existing portfolio overlap;
- deterministic scaffold outputs only as baseline/context evidence, never as a route around hard constraints.

## Forbidden Learned Inputs

Layer 6 must not train on or emit fields that make it an alpha learner, action planner, execution gate, or broker/account mutator.

- future return, future volatility, future fill, future event interpretation, future rating/news/filing interpretation, or any post-decision data;
- buy/sell/hold/open/close/reduce labels, final action labels, order quantity, route, broker response, or account mutation outcome;
- target-specific raw alpha features, target direction labels, single-target future PnL labels, cross-sectional leaderboards, or features that directly choose which target to trade;
- option contract selection, strike, expiry, DTE, Greeks, option route, or execution-specific option fields;
- hard-limit override, kill-switch override, broker permission, or account-control fields.

## Utility And Labels

Layer 6 labels are replay-derived policy utilities, not ordinary classification labels. Each training row should evaluate eligible policy buckets against a deterministic baseline under the same point-in-time state.

Core utility components:

- risk-adjusted portfolio return over the declared horizon;
- realized volatility and drawdown penalty;
- tail-loss / CVaR penalty;
- concentration and correlation-crowding penalty;
- risk-budget and premium-budget breach penalty;
- turnover and policy-instability penalty;
- hard-rule violation invalidation or large penalty;
- missed-safe-opportunity penalty only when it cannot become an alpha reward proxy.

Allowed policy buckets include:

- risk posture: `defensive`, `neutral`, `constructive`;
- premium budget: `closed`, `limited`, `normal`, `expanded`;
- new exposure permission: `deny`, `restricted`, `allow`;
- market/systemic haircut bucket;
- portfolio-capacity bucket;
- policy-stability and confidence bucket.

The learned model may estimate a policy distribution or calibrated utility per bucket, but the emitted state remains the accepted `dynamic_risk_policy_state` surface.

## Candidate Model Family

The final Layer 6 contract permits learned policy implementations that satisfy the objective, boundary, explainability, and validation gates:

- constrained contextual-bandit policy with off-policy evaluation;
- conservative policy-improvement model with doubly robust OPE;
- monotonic calibrated tree / GBM utility scorer with explicit monotonic constraints on stress, drawdown, budget use, and capacity pressure;
- other policy optimizers only when they preserve point-in-time lineage, explainability, hard constraints, and promotion evidence.

The contract does not prefer a weaker transitional implementation. Candidate implementations compete under the same final validation gates.

## Learned Artifact And Explainability

A promoted or promotion-candidate Layer 6 artifact must include:

- model id, schema version, training window, replay window, fold boundaries, and feature schema hash;
- accepted row scopes and output-family schema;
- deterministic baseline references;
- training manifest and label/utility lineage;
- trained artifact payload;
- feature importance, SHAP, monotonic constraint, or policy attribution report;
- policy action distribution by regime and scope;
- calibration curves for permission, confidence, and policy buckets;
- walk-forward portfolio replay report;
- off-policy evaluation report where historical action selection creates counterfactual risk;
- hard-constraint audit;
- leakage audit;
- target-entanglement audit;
- per-scope performance for `global`, `target_candidate`, and `active_position`;
- known invalid regimes and insufficient-evidence conditions.

Dashboard publication should show not only that explainability exists, but whether the artifact primarily depends on global, systemic, and portfolio features rather than target identifiers or target-alpha proxies.

## Validation Gates And Baselines

Layer 6 is promotion-eligible only if walk-forward and replay evidence shows stable risk-adjusted improvement without boundary violations.

Required baselines:

- current deterministic scaffold;
- fixed-risk neutral policy;
- volatility-scaled deterministic policy;
- systemic-pressure haircut rule;
- portfolio-capacity-only rule.

Required gates:

- risk-adjusted portfolio utility beats baselines with stable confidence, not just higher raw PnL;
- drawdown, tail loss, budget breach, concentration, and turnover do not worsen beyond accepted tolerance;
- off-policy evaluation supports non-negative improvement when action counterfactuals matter;
- regime splits pass for high volatility, low volatility, systemic event pressure, earnings-dense windows, and liquidity-stress windows;
- scope isolation passes: removing candidate/position rows must not materially change global policy;
- target permutation passes: target identity, sector identity, or candidate ordering cannot materially drift global budget outputs;
- point-in-time lineage passes for all features and labels;
- hard constraints pass: no forbidden fields, hard-limit override, broker/action/order emission, or account mutation;
- policy stability passes: adjacent-minute policy changes must be justified by state changes;
- production authority remains blocked until the artifact is promoted after shadow evidence.

## Calendar-event pressure

Layer 6 does not own raw trading-calendar event interpretation. Overnight/weekend/holiday closures, early closes, triple-witching, index rebalances, Nasdaq-100 rebalance, and similar scheduled market-structure dates are Layer 4 event-risk families when reviewed evidence shows that the date changes liquidity, forced flow, de-risking, gap behavior, or path risk.

Layer 6 consumes the accepted Layer 4 / Layer 5 pressure from those events. For example, a high `4_event_session_gap_risk_score_<horizon>` or a lowered Layer 5 alpha-tradability/path-quality score can reduce Layer 6 risk budget, premium budget, or new-exposure permission. Layer 6 must not independently infer raw calendar-event risk from the date alone.

## Outputs

- dynamic_risk_policy_state_ref
- policy_scope
- policy_scope_id
- dynamic_risk_policy_state
- dynamic_risk_policy_diagnostics
- 6_* dynamic risk-budget, premium-budget, exposure-permission, haircut, capacity, stability, and confidence score families

## Boundary

Layer 6 does not emit buy/sell/hold, order size, broker route, option contract, account mutation, or hard-limit overrides. Downstream Layer 7 consumes the state when projecting target position state.

Layer 6 must not learn which target is profitable. It learns whether the portfolio can accept, restrict, or deny risk under the current global and portfolio state. If candidate or active-position context causes the global budget to behave like a target selector, the artifact fails the Layer 6 contract.
