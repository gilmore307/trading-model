# tests

First-party tests for `trading-model`.

Tests use in-memory rows and fake cursors. They must not call providers, mutate durable databases, commit generated artifacts, or read secrets.
