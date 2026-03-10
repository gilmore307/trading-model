from __future__ import annotations

import argparse
import json

from src.runtime_mode import set_mode, VALID_MODES


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=sorted(VALID_MODES))
    parser.add_argument('--reason', default=None)
    parser.add_argument('--actor', default='operator')
    args = parser.parse_args()
    payload = set_mode(args.mode, reason=args.reason, actor=args.actor)
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
