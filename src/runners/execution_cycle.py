from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from src.execution.pipeline import ExecutionPipeline
from src.reconcile.alignment import ExchangePositionSnapshot


OUT_DIR = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime')
OUT_DIR.mkdir(parents=True, exist_ok=True)
EXEC_PATH = OUT_DIR / 'latest-execution-cycle.json'


def main() -> None:
    pipeline = ExecutionPipeline()
    result = pipeline.run_cycle(exchange_snapshot=None)
    payload = asdict(result)
    EXEC_PATH.write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False))
    print(json.dumps(payload, indent=2, default=str, ensure_ascii=False))


if __name__ == '__main__':
    main()
