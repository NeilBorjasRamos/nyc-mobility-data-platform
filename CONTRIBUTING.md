# Contributing
Use Python 3.11–3.13. Install uv, then run:
```bash
uv sync --frozen --extra dev
uv run ruff check src tests examples scripts
uv run ruff format --check src tests examples scripts
uv run pytest --cov --cov-fail-under=80 -q
uv build
```
Create a descriptive branch and a focused PR. Explain the behavior, tradeoffs and
validation; a new test should prove an invariant or failure boundary. Keep tests
offline and deterministic. Use conventional commit prefixes such as feat, fix,
test, docs and ci.

Do not commit source data, local databases, .env files, temporary logs or credentials.
Use the issue template with sanitized errors. Bump MODEL_VERSION when output
semantics change. Schema changes also need an explicit migration: a model-version
bump alone cannot migrate physical tables. Update ADRs for architectural changes.

Dependency updates must update pyproject.toml and uv.lock together. Run uv lock
and the complete validation sequence. Do not manually edit the lock file.
Review GitHub Actions dependency updates before merging.
