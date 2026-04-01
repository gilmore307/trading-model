from __future__ import annotations

from dataclasses import asdict
import json

from src.config.settings import Settings
from src.runtime.workflows import OkxWorkflowHooks, run_review_event


def main() -> None:
    settings = Settings.load()
    settings.ensure_demo_only()
    result = run_review_event(hooks=OkxWorkflowHooks(settings))
    print(json.dumps(asdict(result), ensure_ascii=False, default=str, indent=2))


if __name__ == '__main__':
    main()
