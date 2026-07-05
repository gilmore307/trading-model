from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from models.return_distribution_surface import write_surface_bundle_manifest


REPO_ROOT = Path(__file__).resolve().parents[1]


class ReturnDistributionSurfaceBundleTests(unittest.TestCase):
    def test_bundle_manifest_records_surfaces_and_read_only_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            manifest = write_surface_bundle_manifest(
                output_dir=output_dir,
                request={"symbols": ["AAPL"], "windows": [{"start": "2025-01-01", "end_exclusive": "2025-02-01"}]},
                surfaces=[
                    {
                        "symbol": "AAPL",
                        "status": "ready",
                        "surface_summary_path": str(output_dir / "aapl" / "surface_summary.json"),
                    }
                ],
                chain_smoke=[
                    {
                        "symbol": "AAPL",
                        "chain_status": "passed",
                        "handoff_checks_passed": True,
                    }
                ],
            )

            saved = json.loads((output_dir / "surface_bundle_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["contract_type"], "tradable_time_return_distribution_surface_bundle_manifest")
            self.assertEqual(saved["surface_count"], 1)
            self.assertEqual(saved["chain_smoke"][0]["chain_status"], "passed")
            self.assertFalse(saved["side_effects"]["provider_call_performed"])
            self.assertFalse(saved["side_effects"]["sql_mutation_performed"])

    def test_bundle_cli_supports_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/models/build_tradable_time_return_distribution_surface_bundle.py", "--help"],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--symbols", result.stdout)
        self.assertIn("--run-chain-smoke", result.stdout)


if __name__ == "__main__":
    unittest.main()
