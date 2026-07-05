# model_05_option_expression

Canonical package boundary for current `M05 Option Expression`.

This model owns optional option/underlying expression after the unified direct-underlying decision intent exists. It must not choose broker orders, mutate accounts, or absorb the main decision model before option-chain, liquidity, volatility, and structure-specific validation is mature.

The current generator consumes `direct_underlying_intent` / `unified_decision_vector_ref` from M04 plus point-in-time option-chain candidates. It emits `expression_probability_surface` as the primary M05 probability function, plus `expression_candidate_set`, derived `option_expression_plan`, `expression_vector`, and `5_*` score/resolution fields.

M05 reads the path direction from the M04 handoff before falling back to
`action_side`. This preserves bearish option-expression routing when M04 has a
bearish thesis but direct-underlying shorting is blocked.

When M05 compares option contracts with `no_option_expression`, the no-option
candidate is scored as the pure underlying-equity proxy for the M04 thesis. It
is not a cash/no-trade shortcut; no-trade remains owned by the upstream M04
action state.

`expression_probability_surface` is the native M05 comparison surface. It
projects the M04 `thesis_distribution_surface` through point-in-time option
chain, liquidity, Greek, IV, theta, fill, and policy terms into candidate-level
payoff probabilities. `expression_candidate_set` contains the same-shaped
candidate support vectors for the underlying-equity proxy and each point-in-time
option contract candidate, including rejected candidates with their policy
reasons. The existing `option_expression_plan` remains the selected-candidate
compatibility projection used by downstream current-chain consumers until the
final selector is explicitly cut over.
