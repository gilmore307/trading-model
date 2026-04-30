# tests

First-party tests for `trading-model`.

Tests use in-memory rows, fake cursors, and CLI dry-runs. They cover model-output generators, governance SQL helpers, promotion row helpers, and dry-run evaluation harnesses without calling providers, mutating durable databases, committing generated artifacts, or reading secrets.
