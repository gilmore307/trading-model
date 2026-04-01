#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: $0 <tracked-path>" >&2
  exit 1
fi

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_PATH="$1"

cd "$REPO_DIR"

CURRENT_FILE=".git/info/sparse-checkout"
if [ ! -f "$CURRENT_FILE" ]; then
  echo "sparse-checkout is not initialized" >&2
  exit 1
fi

python3 - "$CURRENT_FILE" "$TARGET_PATH" <<'PY'
import sys
from pathlib import Path

file_path = Path(sys.argv[1])
target = sys.argv[2].strip()
lines = file_path.read_text(encoding='utf-8').splitlines()
out = []
for line in lines:
    stripped = line.strip()
    if stripped == target or stripped == f'/{target}' or stripped == f'{target}/' or stripped == f'/{target}/':
        continue
    out.append(line)
file_path.write_text('\n'.join(out).rstrip() + '\n', encoding='utf-8')
PY

git sparse-checkout reapply

echo "excluded sparse path: $TARGET_PATH"
