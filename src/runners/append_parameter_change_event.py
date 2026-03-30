from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUT = Path('data/derived/parameter_change_log.json')
SCHEMA_VERSION = 'parameter_change_log_v1'


def _parse_value(raw: str | None) -> Any:
    if raw is None:
        return None
    text = raw.strip()
    if text == '':
        return None
    lowered = text.lower()
    if lowered == 'null':
        return None
    if lowered == 'true':
        return True
    if lowered == 'false':
        return False
    try:
        if '.' in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Append one parameter change event into data/derived/parameter_change_log.json')
    parser.add_argument('--timestamp', help='ISO timestamp; defaults to now UTC')
    parser.add_argument('--symbol', required=True)
    parser.add_argument('--cluster-id', type=int)
    parser.add_argument('--state-label')
    parser.add_argument('--family', required=True)
    parser.add_argument('--parameter-key', required=True)
    parser.add_argument('--old-value')
    parser.add_argument('--new-value')
    parser.add_argument('--parameter-region-before')
    parser.add_argument('--parameter-region-after')
    parser.add_argument('--change-type', required=True, choices=['candidate', 'reviewed', 'activated', 'rolled_back', 'manual_edit'])
    parser.add_argument('--reason', required=True)
    parser.add_argument('--source', required=True, choices=['research', 'review', 'manual', 'runtime'])
    parser.add_argument('--operator', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--status', required=True, choices=['proposed', 'active', 'superseded', 'reverted', 'deprecated'])
    return parser


def load_existing() -> dict[str, Any]:
    if not OUT.exists():
        return {
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'schemaVersion': SCHEMA_VERSION,
            'events': [],
        }
    return json.loads(OUT.read_text(encoding='utf-8'))


def main() -> None:
    args = build_arg_parser().parse_args()
    payload = load_existing()
    events = payload.get('events') or []

    event = {
        'timestamp': args.timestamp or datetime.now(timezone.utc).isoformat(),
        'symbol': args.symbol,
        'cluster_id': args.cluster_id,
        'state_label': args.state_label,
        'family': args.family,
        'parameter_key': args.parameter_key,
        'old_value': _parse_value(args.old_value),
        'new_value': _parse_value(args.new_value),
        'parameter_region_before': args.parameter_region_before,
        'parameter_region_after': args.parameter_region_after,
        'change_type': args.change_type,
        'reason': args.reason,
        'source': args.source,
        'operator': args.operator,
        'version': args.version,
        'status': args.status,
    }

    events.append(event)
    payload['generatedAt'] = datetime.now(timezone.utc).isoformat()
    payload['schemaVersion'] = payload.get('schemaVersion') or SCHEMA_VERSION
    payload['events'] = events
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(OUT), 'eventCount': len(events), 'appendedVersion': args.version}, ensure_ascii=False))


if __name__ == '__main__':
    main()
