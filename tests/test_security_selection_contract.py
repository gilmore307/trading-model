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
            "`trend_stability_score`",
            "`context_conditioned_stability_score`",
            "`stock_etf_exposure_ref`",
            "`eligibility_state`",
            "`data_quality_score`",
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
        self.assertIn("must not become hidden final stock\nselection", contract)


if __name__ == "__main__":
    unittest.main()
