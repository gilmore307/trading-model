# TRACEABILITY.md

Project rule going forward:

- Every meaningful implementation step should leave a Markdown trail.
- Each node/layer should be documented clearly enough for later audit and resume.
- Prefer small task-scoped MD updates over one giant retrospective dump.

## Minimum standard

For each significant workstream, keep at least one Markdown file that records:

1. **Goal**
2. **Current state**
3. **Inputs / dependencies**
4. **Outputs / artifacts**
5. **Open risks / assumptions**
6. **Next step**

## For review/performance ingestion work

Track:

- canonical source fields
- where each metric is produced
- where each metric is persisted
- where each metric is aggregated
- where each metric is surfaced in reports

## Preferred style

- short, explicit, timestamp-friendly
- no vague "done some refactor" notes
- name files, modules, and commits concretely

This file is a standing constraint for future work in this repo.
