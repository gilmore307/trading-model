import os
import unittest
from pathlib import Path
from unittest import mock

from model_governance.common.sql import database_url
from model_runtime import config


class ModelRuntimeConfigTests(unittest.TestCase):
    def test_runtime_roots_use_environment_overrides(self) -> None:
        with mock.patch.dict(os.environ, {"TRADING_PROJECTS_ROOT": "/tmp/projects", "TRADING_DATA_ROOT": "/tmp/data"}, clear=False):
            self.assertEqual(config.projects_root(), Path("/tmp/projects"))
            self.assertEqual(config.trading_data_root(), Path("/tmp/data"))
            self.assertEqual(config.model_root(), Path("/tmp/projects/trading-model"))

    def test_database_url_prefers_model_specific_environment(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "TRADING_MODEL_DATABASE_URL": "postgresql://model-specific",
                "OPENCLAW_DATABASE_URL": "postgresql://openclaw",
            },
            clear=False,
        ):
            self.assertEqual(database_url(), "postgresql://model-specific")


if __name__ == "__main__":
    unittest.main()
