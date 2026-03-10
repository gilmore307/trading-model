from __future__ import annotations

import json
from pathlib import Path

from src.runtime_mode import load_mode_state

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
OUT = ROOT / 'logs' / 'service' / 'mode.json'
OUT.parent.mkdir(parents=True, exist_ok=True)

payload = load_mode_state()
OUT.write_text(json.dumps(payload, indent=2))
print(json.dumps(payload, indent=2))
