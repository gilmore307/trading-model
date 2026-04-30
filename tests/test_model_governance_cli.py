from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ModelGovernanceCliTests(unittest.TestCase):
    def test_default_cli_writes_sql_file_without_database_connection(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "model_governance_schema.sql"
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/ensure_model_governance_schema.py",
                    "--sql-output",
                    str(output_path),
                ],
                cwd=repo_root,
                env={"PYTHONPATH": "src"},
                text=True,
                capture_output=True,
                check=True,
            )
            sql_text = output_path.read_text(encoding="utf-8")

        self.assertIn("DRY RUN ONLY", result.stdout)
        self.assertIn("no database connection", result.stdout)
        self.assertIn('CREATE TABLE IF NOT EXISTS "trading_model"."model_dataset_request"', sql_text)

    def test_apply_flag_is_required_before_cli_reads_database_url(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        script_text = (repo_root / "scripts" / "ensure_model_governance_schema.py").read_text(encoding="utf-8")

        self.assertIn("if not args.apply:", script_text)
        self.assertIn("--apply", script_text)
        self.assertIn("DRY RUN ONLY", script_text)


if __name__ == "__main__":
    unittest.main()
