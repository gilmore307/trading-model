"""Codex CLI helpers for script-called review agents."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


DEFAULT_CODEX_MODEL = "gpt-5.5"


def invoke_codex_cli(
    *,
    prompt: str,
    codex_bin: str = "codex",
    model: str | None = None,
    timeout_seconds: int = 600,
    sandbox: str = "read-only",
    workdir: str | None = None,
) -> str:
    """Run Codex CLI and return the final assistant message text."""

    resolved_model = (model or DEFAULT_CODEX_MODEL).strip() or DEFAULT_CODEX_MODEL
    resolved_workdir = workdir or os.getcwd()
    with tempfile.NamedTemporaryFile(prefix="codex-review-", suffix=".json", delete=False) as final_file:
        final_output_path = final_file.name
    command = [
        codex_bin,
        "exec",
        "--ephemeral",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--sandbox",
        sandbox,
        "-C",
        resolved_workdir,
        "--output-last-message",
        final_output_path,
        "-m",
        resolved_model,
        prompt,
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False, timeout=timeout_seconds + 30)
    try:
        final_text = Path(final_output_path).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        final_text = ""
    try:
        Path(final_output_path).unlink(missing_ok=True)
    except OSError:
        pass
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        raise SystemExit(result.returncode)
    return final_text or result.stdout
