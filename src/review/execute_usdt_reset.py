from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
PLAN = ROOT / 'reports' / 'changes' / 'prepare-usdt-reset-plan.json'
OUT = ROOT / 'reports' / 'changes' / 'latest-usdt-reset-execution.json'


def main() -> None:
    payload = {
        'generated_at': datetime.now(UTC).isoformat(),
        'type': 'execute_usdt_reset_stub',
        'status': 'not_implemented_live',
        'note': 'Execution step intentionally stubbed for now; plan file should be reviewed and then wired to live spot conversions in demo mode.',
        'plan_exists': PLAN.exists(),
    }
    OUT.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
