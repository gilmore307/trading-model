# model_09_option_expression

Physical package for the Layer 9 `OptionExpressionModel` / trading-guidance option-expression scaffold.

Owns local conversion from Layer 8 `underlying_action_plan` / option-expression handoff fields plus point-in-time option-chain candidates into `option_expression_plan` and `expression_vector` rows. The scaffold implements:

- long-call / long-put / no-option expression resolution from the Layer 8 underlying path thesis;
- point-in-time contract candidate scoring across DTE, delta/Greeks, IV, spread/liquidity, fill quality, and reward/risk;
- selected contract references and option-expression constraints without order routing;
- explicit option-surface status rows for optionable, missing-chain, and non-optionable direct-underlying routes;
- offline option-expression labels and leakage assertions in `evaluation.py`.

Training should use dense minute-level option-expression status rows wherever Layer 8 thesis context exists. Optionable rows with point-in-time option-chain snapshots train contract/expression selection; optionable rows without a snapshot and non-optionable routes such as BTC preserve bypass/no-option status without pretending to score missing contracts. Selected-contract thresholds and expression hard filters are outputs or routing policies, not training-row admission filters.

Boundary: this package may select option-expression and contract constraints, but must not emit order type, route, final order quantity, broker order id, execution instruction, or broker/account mutation fields.
