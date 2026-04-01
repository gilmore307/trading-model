from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description='Delete local reserve heavy variant payloads after remote sync confirmation.')
    parser.add_argument('--family-dir', required=True, help='Family artifact directory containing summary.json and variants/*.json')
    parser.add_argument('--apply', action='store_true', help='Actually delete reserve variant payloads. Default is dry-run.')
    args = parser.parse_args()

    family_dir = Path(args.family_dir)
    summary_path = family_dir / 'summary.json'
    variants_dir = family_dir / 'variants'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    reserve_ids = set(summary.get('reserve_variant_ids', []))

    deleted = 0
    for variant_id in sorted(reserve_ids):
        safe_variant = ''.join(ch for ch in variant_id if ch.isalnum() or ch in {'_', '-'})
        variant_path = variants_dir / f'{safe_variant}.json'
        if not variant_path.exists():
            continue
        if args.apply:
            variant_path.unlink()
        deleted += 1
        print(json.dumps({
            'variant_id': variant_id,
            'path': str(variant_path),
            'status': 'deleted' if args.apply else 'would_delete',
        }, ensure_ascii=False))

    print(json.dumps({'family_dir': str(family_dir), 'reserve_variant_count': len(reserve_ids), 'processed': deleted, 'apply': bool(args.apply)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
