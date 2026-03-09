from __future__ import annotations

import json
from datetime import datetime, UTC
from zoneinfo import ZoneInfo
from pathlib import Path

BJ = ZoneInfo('Asia/Shanghai')
ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
OUT = ROOT / 'logs' / 'service' / 'mode.json'
OUT.parent.mkdir(parents=True, exist_ok=True)

now_utc = datetime.now(UTC)
now_bj = now_utc.astimezone(BJ)
mode = 'review' if (now_bj.weekday() == 6 and now_bj.hour == 0) else 'trade'

payload = {
    'generated_at': now_utc.isoformat(),
    'mode': mode,
    'bj_time': now_bj.isoformat(),
    'utc_time': now_utc.isoformat(),
}
OUT.write_text(json.dumps(payload, indent=2))
print(json.dumps(payload, indent=2))
