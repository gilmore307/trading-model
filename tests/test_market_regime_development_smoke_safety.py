from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts/models/model_01_market_regime/run_market_regime_development_smoke.py"
SPEC = importlib.util.spec_from_file_location("run_market_regime_development_smoke", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
SMOKE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SMOKE)


class MarketRegimeDevelopmentSmokeSafetyTests(unittest.TestCase):
    def test_development_smoke_uses_isolated_schema_names(self) -> None:
        self.assertEqual(SMOKE.SOURCE_SCHEMA, "trading_model_development_smoke")
        self.assertEqual(SMOKE.FEATURE_SCHEMA, "trading_model_development_smoke")
        self.assertEqual(SMOKE.MODEL_SCHEMA, "trading_model_development_smoke")

    def test_development_smoke_requires_explicit_database_mutation_confirmation(self) -> None:
        with self.assertRaisesRegex(SystemExit, "confirm-development-db-mutation"):
            SMOKE._require_database_mutation_confirmation(
                SimpleNamespace(confirm_development_db_mutation=None, database_url="postgresql://localhost/dev")
            )

    def test_development_smoke_requires_explicit_database_url(self) -> None:
        with self.assertRaisesRegex(SystemExit, "explicit --database-url"):
            SMOKE._require_database_mutation_confirmation(
                SimpleNamespace(
                    confirm_development_db_mutation=SMOKE.CONFIRM_DATABASE_MUTATION_TOKEN,
                    database_url=None,
                )
            )

    def test_run_smoke_rechecks_confirmation_before_loading_or_mutating(self) -> None:
        with self.assertRaisesRegex(SystemExit, "confirm-development-db-mutation"):
            SMOKE.run_smoke(SimpleNamespace(confirm_development_db_mutation=None, database_url="postgresql://localhost/dev"))


if __name__ == "__main__":
    unittest.main()
