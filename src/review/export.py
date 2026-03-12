from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.review.report import build_report_scaffold
from src.review.framework import ReviewWindow


DEFAULT_REPORTS_DIR = Path('/root/.openclaw/workspace/projects/crypto-trading/reports/trade-review')


def _slug(label: str) -> str:
    return label.replace(':', '_').replace('->', '__').replace('/', '-').replace(' ', '_')


def render_report_markdown(report: dict[str, Any]) -> str:
    meta = report.get('meta', {}) if isinstance(report, dict) else {}
    lines = [
        f"# Trade Review - {meta.get('label', 'unknown')}",
        '',
        f"- Cadence: {meta.get('cadence')}",
        f"- Window: {meta.get('window_start')} -> {meta.get('window_end')}",
        f"- Generated at: {meta.get('generated_at')}",
        '',
        '## Executive Summary',
    ]

    for bullet in report.get('executive_summary', {}).get('bullets', []):
        lines.append(f"- {bullet}")

    lines.extend(['', '## Recommended Actions'])
    actions = report.get('recommended_actions', [])
    if not actions:
        lines.append('- None')
    else:
        for action in actions:
            target = action.get('target_account') or 'global'
            lines.append(f"- [{action.get('priority')}] {action.get('title')} ({target}) — {action.get('reason')}")

    narrative_blocks = report.get('narrative_blocks', [])
    for block in narrative_blocks:
        lines.extend(['', f"## {block.get('title')}"])
        block_lines = block.get('lines', [])
        if not block_lines:
            lines.append('- None')
        else:
            for line in block_lines:
                lines.append(f"- {line}")

    lines.extend(['', '## Section Status'])
    for section in report.get('sections', []):
        lines.append(f"- {section.get('title')}: {section.get('status')}")

    return '\n'.join(lines).strip() + '\n'


def _write_latest_pointers(out_root: Path, cadence: str, json_path: Path, md_path: Path) -> None:
    latest_json = out_root / f'latest_{cadence}.json'
    latest_md = out_root / f'latest_{cadence}.md'
    latest_json.write_text(json_path.read_text(encoding='utf-8'), encoding='utf-8')
    latest_md.write_text(md_path.read_text(encoding='utf-8'), encoding='utf-8')


def _update_report_index(out_root: Path, report: dict[str, Any], json_path: Path, md_path: Path) -> Path:
    index_path = out_root / 'index.json'
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding='utf-8'))
        except Exception:
            index = {}
    else:
        index = {}

    if not isinstance(index, dict):
        index = {}
    reports = index.get('reports')
    if not isinstance(reports, list):
        reports = []

    meta = report.get('meta', {}) if isinstance(report, dict) else {}
    cadence = str(meta.get('cadence') or 'unknown')
    entry = {
        'label': meta.get('label'),
        'cadence': cadence,
        'generated_at': meta.get('generated_at'),
        'json_path': str(json_path),
        'markdown_path': str(md_path),
    }
    reports.append(entry)
    reports = reports[-50:]

    latest_by_cadence: dict[str, dict[str, Any]] = {}
    for row in reports:
        if not isinstance(row, dict):
            continue
        row_cadence = str(row.get('cadence') or 'unknown')
        latest_by_cadence[row_cadence] = row

    index = {
        'reports': reports,
        'latest_by_cadence': latest_by_cadence,
    }
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding='utf-8')
    return index_path


def export_report_artifacts(
    window: ReviewWindow,
    *,
    compare_snapshot: dict[str, Any] | None = None,
    metrics_by_account: dict[str, dict[str, Any]] | None = None,
    history_path: str | None = None,
    out_dir: str | Path | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    report = build_report_scaffold(window, compare_snapshot=compare_snapshot, metrics_by_account=metrics_by_account, history_path=history_path)
    out_root = Path(out_dir) if out_dir is not None else DEFAULT_REPORTS_DIR
    out_root.mkdir(parents=True, exist_ok=True)

    stamp = (generated_at or datetime.now(UTC)).astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')
    label = _slug(report.get('meta', {}).get('label', 'trade_review'))
    base = out_root / f'{stamp}_{label}'
    json_path = base.with_suffix('.json')
    md_path = base.with_suffix('.md')

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    md_path.write_text(render_report_markdown(report), encoding='utf-8')

    cadence = str(report.get('meta', {}).get('cadence') or 'unknown')
    _write_latest_pointers(out_root, cadence, json_path, md_path)
    index_path = _update_report_index(out_root, report, json_path, md_path)

    return {
        'report': report,
        'json_path': str(json_path),
        'markdown_path': str(md_path),
        'latest_json_path': str(out_root / f'latest_{cadence}.json'),
        'latest_markdown_path': str(out_root / f'latest_{cadence}.md'),
        'index_path': str(index_path),
    }
