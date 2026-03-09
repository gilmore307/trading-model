#!/usr/bin/env bash
set -euo pipefail
cd /root/openclaw-automation
source .venv/bin/activate
python -m src.runner.live_trader --arm-demo-submit
