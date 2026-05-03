# common

Shared low-level helpers for model governance packages.

- `sql.py` owns SQL identifier quoting, SQL/JSON literal rendering, database URL resolution, and `psql` execution.
- This package must stay dependency-light and must not import model-specific code, runtime scripts, evaluation, or promotion modules.

Use this package when multiple governance areas need the same primitive helper. Do not put dataset/evaluation policy or promotion lifecycle rules here.
