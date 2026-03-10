from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from src.runtime_mode import set_mode, VALID_MODES, load_mode_state

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
TEST_SUMMARY_PATH = ROOT / 'reports' / 'changes' / 'latest-test-mode-summary.json'


def assert_test_mode_can_start() -> None:
    current = load_mode_state()
    if current.get('mode') == 'test':
        raise RuntimeError('test mode is already active')
    if TEST_SUMMARY_PATH.exists():
        try:
            payload = json.loads(TEST_SUMMARY_PATH.read_text())
            generated_at = payload.get('generated_at')
            if generated_at:
                then = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
                age = (datetime.now(UTC) - then).total_seconds()
                if age < 600:
                    raise RuntimeError(f'test mode cooldown active: last summary age {age:.1f}s < 600s')
        except RuntimeError:
            raise
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=sorted(VALID_MODES))
    parser.add_argument('--reason', default=None)
    parser.add_argument('--actor', default='operator')
    args = parser.parse_args()
    if args.mode == 'test':
        assert_test_mode_can_start()
    payload = set_mode(args.mode, reason=args.reason, actor=args.actor)
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
