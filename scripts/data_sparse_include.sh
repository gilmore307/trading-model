#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: $0 <tracked-path>" >&2
  exit 1
fi

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_PATH="$1"

cd "$REPO_DIR"

git sparse-checkout init --cone >/dev/null 2>&1 || true
git sparse-checkout add "$TARGET_PATH"

echo "included sparse path: $TARGET_PATH"
