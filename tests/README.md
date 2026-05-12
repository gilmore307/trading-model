# tests

First-party tests for `trading-model`.

- `test_realtime_decision_handoff.py` covers `execution_model_decision_input_snapshot` validation and `model_realtime_decision_route_plan` fixture/shadow routing without model activation.

Tests use in-memory rows, fake cursors, local fallback reviews, and CLI dry-runs. They cover model-output generators, deterministic Layer 4/5/6/7/8 scaffolds, governance SQL helpers, promotion row helpers, agent-review prompt validation, and dry-run evaluation harnesses without calling providers, mutating durable databases, committing generated artifacts, invoking live agents, or reading secrets.
