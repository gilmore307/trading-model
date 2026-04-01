from __future__ import annotations

import argparse
from datetime import UTC, datetime

from src.runtime.strategy_pointer import ActiveStrategySnapshot, store_active_strategy_snapshot


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Promote a strategy snapshot by updating the active strategy pointer.')
    parser.add_argument('--version', required=True, help='New active strategy version label.')
    parser.add_argument('--family', default='default', help='Strategy family name.')
    parser.add_argument('--config-path', default='', help='Path to the promoted strategy config/artifact.')
    parser.add_argument('--source', default='manual_promotion', help='Pointer source label.')
    parser.add_argument('--promotion-note', default='', help='Optional promotion note.')
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    now = datetime.now(UTC).isoformat()
    snapshot = ActiveStrategySnapshot(
        version=args.version,
        updated_at=now,
        source=args.source,
        metadata={
            'family': args.family,
            'config_path': args.config_path,
            'promoted_at': now,
            'promotion_note': args.promotion_note,
        },
    )
    store_active_strategy_snapshot(snapshot)
    print(f'promoted strategy: version={args.version} family={args.family} source={args.source}')


if __name__ == '__main__':
    main()
