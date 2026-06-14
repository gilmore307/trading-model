# model_04_unified_decision

Canonical package boundary for current `M04 Unified Decision`.

This model owns after-cost alpha, risk policy, exposure projection, and direct-underlying action as one decision model contract. It should still expose structured heads for edge, risk, exposure, and action so downstream systems can audit and route decisions without rebuilding a serial Layer 5-8 chain.

`trade_intensity_score` is the raw exposure-gap magnitude. Use `materiality_adjusted_action_score` for action ranking because it gates raw intensity by configured materiality, then weighs confidence, entry quality, downside risk, and no-trade pressure.
