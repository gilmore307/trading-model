# model_08_option_expression

Legacy physical package for the conceptual Layer 7 `OptionExpressionModel` / trading-guidance option-expression scaffold.

Owns local conversion from Layer 6 `underlying_action_plan` / Layer 7 trading-guidance handoff fields plus point-in-time option-chain candidates into `option_expression_plan` and `expression_vector` rows. The scaffold implements:

- long-call / long-put / no-option expression resolution from the conceptual Layer 6 underlying path thesis;
- point-in-time contract candidate scoring across DTE, delta/Greeks, IV, spread/liquidity, fill quality, and reward/risk;
- selected contract references and option-expression constraints without order routing;
- offline option-expression labels and leakage assertions in `evaluation.py`.

Boundary: this package may select option-expression and contract constraints, but must not emit order type, route, final order quantity, broker order id, execution instruction, or broker/account mutation fields.
