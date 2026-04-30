# tests

First-party tests for `trading-model`.

Tests use in-memory rows and fake cursors. They cover model-output generators and governance SQL helpers without calling providers, mutating durable databases, committing generated artifacts, or reading secrets.
