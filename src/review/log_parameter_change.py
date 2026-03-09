from __future__ import annotations

import argparse
import json
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
OUT_DIR = ROOT / 'reports' / 'changes'
OUT_DIR.mkdir(parents=True, exist_ok=True)
LATEST = OUT_DIR / 'latest-parameter-change.json'
LOG = OUT_DIR / 'parameter-changes.jsonl'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    parser.add_argument('--old', required=True)
    parser.add_argument('--new', required=True)
    parser.add_argument('--reason', required=True)
    parser.add_argument('--scope', default='global')
    args = parser.parse_args()

    payload = {
        'generated_at': datetime.now(UTC).isoformat(),
        'scope': args.scope,
        'target': args.target,
        'old': args.old,
        'new': args.new,
        'reason': args.reason,
    }
    LATEST.write_text(json.dumps(payload, indent=2))
    with LOG.open('a') as f:
        f.write(json.dumps(payload) + '\n')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
