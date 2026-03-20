# Documentation Policy

Project rule going forward:
- project Markdown belongs under `docs/`
- repo-local session handoff files do not belong in the project root
- topic/session continuity belongs in the workspace memory system, not scattered through this repo
- every meaningful implementation step should still leave a durable documentation trail

## Minimum standard

For each significant workstream, keep at least one Markdown file that records:
1. goal
2. current state
3. inputs / dependencies
4. outputs / artifacts
5. open risks / assumptions
6. next step

## Preferred style

- short, explicit, timestamp-friendly
- no vague “did some refactor” notes
- name files, modules, and behaviors concretely
- when a doc becomes obsolete, either update it or delete it; do not let root-level doc clutter accumulate again

## Working rule

Use:
- `docs/project-status.md` for current state
- `docs/TODO.md` for current tasks
- topic-specific docs under `docs/` for architecture/runbooks
