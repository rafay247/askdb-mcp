# Repository Guidelines

## Project Structure & Module Organization

This repository contains a small Python package, `askdb_mcp`, for a local MCP server that turns natural language into validated SQLite queries. Source code lives in `askdb_mcp/`: `server.py` starts the MCP and FastAPI process, `service.py` coordinates request handling, `openai_sql_generator.py` calls OpenAI, `sql_validator.py` guards SQL safety, and `sqlite_executor.py` runs approved statements. Tests live in `tests/` and mirror the main modules. Design notes are in `docs/design.md`; setup and usage examples are in `README.md`.

## Build, Test, and Development Commands

- `python -m venv .venv` and `source .venv/bin/activate`: create and activate a local virtual environment.
- `pip install -e ".[dev]"`: install the package in editable mode with pytest.
- `askdb-mcp`: run the MCP server on stdio and the local FastAPI approval API on `127.0.0.1:8765`.
- `python -m py_compile askdb_mcp/*.py`: quick syntax check for package modules.
- `pytest`: run the full test suite configured by `pyproject.toml`.

## Coding Style & Naming Conventions

Use Python 3.11+ syntax and keep modules focused by responsibility. Follow standard PEP 8 conventions: four-space indentation, `snake_case` for functions and variables, `PascalCase` for classes and dataclasses, and clear module names such as `pending_store.py`. Prefer explicit validation and typed data models over ad hoc dictionaries when crossing module boundaries. Keep comments brief and only where they clarify non-obvious behavior.

## Testing Guidelines

Tests use `pytest` and are discovered under `tests/`. Name files `test_<module>.py` and test functions `test_<behavior>()`. Add focused unit tests for validators, pending write flow, SQLite execution, and service decisions. When changing SQL safety rules or write approval behavior, include both allowed and rejected cases.

## Commit & Pull Request Guidelines

The current Git history uses short imperative summaries, for example `Build askdb MCP server`. Keep commits concise and scoped to one logical change. Pull requests should include a short description, test results such as `pytest`, and any configuration or security implications. Link related issues when available and include API examples when behavior changes.

## Security & Configuration Tips

Do not commit secrets or local database files. Configure runtime values through environment variables: `OPENAI_API_KEY`, `SQLITE_DB_PATH`, and `ASKDB_API_KEY`. Keep `ASKDB_API_KEY` non-empty for local approval endpoints, and remember that schema metadata may be sent to OpenAI while query result rows should remain local.
