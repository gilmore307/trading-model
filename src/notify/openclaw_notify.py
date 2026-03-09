from __future__ import annotations

import json
import subprocess
from typing import Optional


class OpenClawNotifier:
    def __init__(self, channel: str = "discord", target: Optional[str] = None):
        self.channel = channel
        self.target = target

    def send(self, text: str) -> dict:
        cmd = [
            "openclaw",
            "message",
            "send",
            "--channel",
            self.channel,
        ]
        if self.target:
            cmd += ["--target", self.target]
        cmd += ["--message", text]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "command": json.dumps(cmd),
        }
