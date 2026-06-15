# askdb_mcp

`askdb_mcp` is a local Python MCP server for asking a SQLite database questions in natural language. It uses OpenAI to generate SQL, executes read queries after validation, and requires FastAPI approval before running `INSERT`, `UPDATE`, or `DELETE`.

## Features

- MCP tool: `askdb_ask_database`
- Fixed local SQLite database path from `SQLITE_DB_PATH`
- OpenAI Responses API with structured SQL output
- SQL validation for single-statement SQLite queries
- Read queries execute immediately
- Write queries are stored as pending proposals
- FastAPI approval endpoints protected by `X-AskDB-Key`

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Configure

```bash
create .env
export OPENAI_API_KEY="sk-your-key"
export SQLITE_DB_PATH="/absolute/path/to/database.sqlite"
export ASKDB_API_KEY="change-me-local-key"
```

## Run

```bash
askdb-mcp
```

The MCP server runs on stdio. The FastAPI approval server starts in the same process on `127.0.0.1:8765` by default.

## Approval API

```bash
curl -H "X-AskDB-Key: $ASKDB_API_KEY" http://127.0.0.1:8765/pending-writes
curl -X POST -H "X-AskDB-Key: $ASKDB_API_KEY" http://127.0.0.1:8765/pending-writes/{id}/approve
curl -X POST -H "X-AskDB-Key: $ASKDB_API_KEY" http://127.0.0.1:8765/pending-writes/{id}/reject
```

## MCP Client Example

```json
{
  "mcpServers": {
    "askdb_mcp": {
      "command": "askdb-mcp",
      "env": {
        "OPENAI_API_KEY": "sk-your-key",
        "SQLITE_DB_PATH": "/absolute/path/to/database.sqlite",
        "ASKDB_API_KEY": "change-me-local-key"
      }
    }
  }
}
```

## Verify

```bash
python -m py_compile askdb_mcp/*.py
pytest
```

