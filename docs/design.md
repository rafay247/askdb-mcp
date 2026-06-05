# askdb_mcp Design

## Understanding Summary

- Build a local Python MCP server named `askdb_mcp`.
- Use FastAPI for local HTTP write approval endpoints.
- Connect to one fixed local SQLite database path from configuration.
- Accept natural language questions and commands from an AI agent.
- Use the OpenAI API to translate natural language into SQL.
- Execute read-only SQL immediately after validation.
- Require explicit HTTP approval before executing `INSERT`, `UPDATE`, or `DELETE`.

## Assumptions

- The server is for one local developer and one local SQLite database.
- FastAPI binds to `127.0.0.1` by default.
- Approval endpoints require an `X-AskDB-Key` API key.
- Schema-changing SQL is blocked in version 1.
- Natural language prompts and schema metadata may be sent to OpenAI.
- Query result rows are not sent to OpenAI.
- Pending write proposals are kept in memory for version 1.

## Decision Log

- Project name: `askdb_mcp`.
- Runtime: Python.
- MCP framework: Python MCP SDK with FastMCP.
- HTTP framework: FastAPI.
- LLM provider: OpenAI.
- Database: SQLite fixed by `SQLITE_DB_PATH`.
- Architecture: one local process hosts MCP tools and FastAPI approval routes.
- Write flow: propose first, approve through FastAPI, then execute exact stored SQL.
- Out of scope: multi-user auth, arbitrary DB paths, schema migrations through natural language.

## Final Design

The server exposes an MCP tool named `askdb_ask_database`. The tool receives a natural language request, introspects the configured SQLite schema, sends the question and schema to OpenAI, validates the returned SQL, and either executes it or creates a pending write proposal.

Read-only `SELECT` and `WITH` queries execute immediately. The response includes SQL, explanation, columns, rows, and row count.

Write queries using `INSERT`, `UPDATE`, or `DELETE` are stored as pending writes and are not executed by the MCP tool. The MCP response includes a pending write ID, SQL, explanation, and approval instructions.

FastAPI exposes `GET /health`, `GET /pending-writes`, `GET /pending-writes/{id}`, `POST /pending-writes/{id}/approve`, and `POST /pending-writes/{id}/reject`. All pending write routes require the configured API key.

SQL validation rejects multiple statements, unsupported statement types, comments, and schema-changing or attachment statements such as `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `ATTACH`, `DETACH`, and unsafe `PRAGMA` usage.

The implementation is intentionally small and modular: configuration, schema inspection, SQL generation, validation, SQLite execution, pending write storage, MCP tools, and FastAPI routes live in separate modules.
