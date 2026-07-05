# model_04_unified_decision

Canonical package boundary for current `M04 Unified Decision`.

This model owns the final direct-underlying posterior probability surface. It
builds `thesis_distribution_surface` by applying M01 and M03 distribution
operators to the M02 target base distribution, then derives after-cost edge,
risk policy, exposure projection, and direct-underlying action as one decision
summary contract. It should still expose structured heads for edge, risk,
exposure, and action so downstream systems can audit and route decisions without
rebuilding the retired alpha/risk/projection/action chain.

`trade_intensity_score` is the raw exposure-gap magnitude. Use `materiality_adjusted_action_score` for action ranking because it gates raw intensity by configured materiality, then weighs confidence, entry quality, downside risk, and no-trade pressure.

M04 keeps direction separate from trade eligibility. `direction_thesis` /
`direction_thesis_score` describe the point-in-time bullish, bearish, or neutral
path view; `direction_certainty_score` describes confidence without sign;
`action_side` describes only the direct-underlying position action. A bearish
path can therefore be handed to M05 even when direct shorting is blocked.
