# model_05_option_expression

Canonical package boundary for current `M05 Option Expression`.

This model owns optional option/underlying expression after the unified direct-underlying decision intent exists. It must not choose broker orders, mutate accounts, or absorb the main decision model before option-chain, liquidity, volatility, and structure-specific validation is mature.

The current generator consumes `direct_underlying_intent` / `unified_decision_vector_ref` from M04 plus point-in-time option-chain candidates. It emits `option_expression_plan`, `expression_vector`, and `5_*` score/resolution fields.
