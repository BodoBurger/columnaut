# AGENTS.md

This file provides repository-specific guidance for coding agents. See `README.md` for the
product overview, setup instructions, and documented behavior.

## Project structure

- `app.py` contains the Streamlit user interface.
- `src/columnaut/ingestion/` contains file adapters and import-time structural checks.
- `src/columnaut/profiling/` contains deterministic dataset and column profiling.
- `src/columnaut/models.py` contains shared result models.
- `tests/` contains the automated test suite.

Keep ingestion and profiling independent of Streamlit so they remain reusable from other
interfaces. Put user-interface behavior in `app.py` and domain behavior in `src/columnaut/`.

## Data and AI boundaries

- Preserve uploaded source data. Report suspicious values or structure; do not silently clean,
  coerce, delete, or replace them.
- Treat pseudo-missing markers, sentinel values, and generic sensibility checks as findings, not
  automatic cleaning rules.
- Keep profile calculations and findings deterministic and testable in Python.
- Represent uncertainty explicitly through the existing severity and confidence concepts.
- AI-assisted features should interpret structured profiling results and propose user-approved
  actions. Do not use an LLM to calculate statistics or send it the full raw dataset by default.

## Implementation conventions

- Support Python 3.11 and follow the existing `src/` package layout.
- Prefer small changes that preserve current public behavior unless the task explicitly changes
  that behavior.
- Add or update tests for behavioral changes and bug fixes.
- Follow the Ruff configuration in `pyproject.toml`; the configured line length is 100 characters.
- Preserve unrelated changes already present in the working tree.

## Verification

Before completing a code change, run the relevant focused tests and then, when practical, the
full checks:

```text
pytest
ruff check app.py src tests
```

If a check cannot be run, state which check was skipped and why.
