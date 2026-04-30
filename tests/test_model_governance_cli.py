from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class ModelGovernanceCliTests(unittest.TestCase):
    def test_governance_cli_dry_run_prints_sql_without_database_connection(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "scripts/ensure_model_governance_schema.py", "--dry-run"],
            cwd=repo_root,
            env={"PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("DRY RUN ONLY", result.stdout)
        self.assertIn("no database connection", result.stdout)
        self.assertIn('CREATE TABLE IF NOT EXISTS "trading_model"."model_dataset_request"', result.stdout)

    def test_governance_cli_default_connects_to_database_path(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        script_text = (repo_root / "scripts" / "ensure_model_governance_schema.py").read_text(encoding="utf-8")

        self.assertIn("if args.dry_run:", script_text)
        self.assertIn('["psql", database_url', script_text)
        self.assertNotIn("--sql-output", script_text)
        self.assertNotIn("psycopg", script_text)

    def test_cleanup_cli_is_destructive_only_with_confirm_token(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "scripts/clear_model_development_database.py", "--dry-run"],
            cwd=repo_root,
            env={"PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=True,
        )
        script_text = (repo_root / "scripts" / "clear_model_development_database.py").read_text(encoding="utf-8")

        self.assertIn('DROP SCHEMA IF EXISTS "trading_model" CASCADE;', result.stdout)
        self.assertIn("DRY RUN ONLY", result.stdout)
        self.assertIn("CONFIRM_TOKEN", script_text)
        self.assertIn("clear-trading-model-development-database", script_text)
        self.assertIn('["psql", database_url', script_text)
        self.assertNotIn("psycopg", script_text)


if __name__ == "__main__":
    unittest.main()
