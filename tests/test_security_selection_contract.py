from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "src" / "models" / "model_02_security_selection" / "sector_context_state_contract.md"


class SecuritySelectionContractTests(unittest.TestCase):
    def test_sector_context_state_contract_names_required_fields(self) -> None:
        contract = CONTRACT_PATH.read_text(encoding="utf-8")

        for token in {
            "trading_model.model_02_security_selection",
            "sector_context_state[available_time, sector_or_industry_symbol]",
            "`available_time`",
            "`sector_or_industry_symbol`",
            "`market_context_state_ref`",
            "`2_trend_stability_score`",
            "`2_conditional_beta_score`",
            "`2_directional_coupling_score`",
            "`2_volatility_response_score`",
            "`2_capture_asymmetry_score`",
            "`2_response_convexity_score`",
            "`2_context_support_score`",
            "`2_context_conditioned_stability_score`",
            "`2_sector_handoff_state`",
            "`2_sector_handoff_rank`",
            "`2_sector_handoff_reason_codes`",
            "`2_eligibility_state`",
            "`2_data_quality_score`",
        }:
            self.assertIn(token, contract)

    def test_sector_context_state_contract_preserves_layer_boundary(self) -> None:
        contract = CONTRACT_PATH.read_text(encoding="utf-8")

        for forbidden_boundary in {
            "final selected stock symbols",
            "strategy family choice",
            "option contract",
            "future returns or realized PnL",
            "hand-written sector labels used as input truth",
        }:
            self.assertIn(forbidden_boundary, contract)
        self.assertIn("ETF holdings and `stock_etf_exposure` are not used as Layer 2 core behavior-model inputs", contract)
        self.assertIn("selected Layer 2 baskets", contract)
        self.assertIn("must not copy Layer 1 market-property factor names", contract)
        self.assertIn("not reused Layer 1 market-property factors", contract)
        self.assertIn("V1 prefers signed axes", contract)
        self.assertIn("positive = upside-favorable capture; negative = downside-heavy capture", contract)


if __name__ == "__main__":
    unittest.main()
