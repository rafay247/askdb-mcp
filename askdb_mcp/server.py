"""MCP stdio server plus local FastAPI approval server."""

from __future__ import annotations

import threading

import uvicorn
from mcp.server.fastmcp import FastMCP

from askdb_mcp.api import create_app
from askdb_mcp.config import load_settings
from askdb_mcp.openai_sql_generator import OpenAISqlGenerator
from askdb_mcp.pending_store import PendingWriteStore
from askdb_mcp.schema_service import SchemaService
from askdb_mcp.service import AskDBService
from askdb_mcp.sqlite_executor import SQLiteExecutor


mcp = FastMCP("askdb_mcp")
_service: AskDBService | None = None


@mcp.tool(
    name="askdb_ask_database",
    annotations={
        "title": "Ask SQLite Database",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def askdb_ask_database(question: str) -> str:
    """Ask the configured SQLite database a natural language question.

    Read-only SQL is executed immediately after validation. INSERT, UPDATE, and
    DELETE statements return a pending write ID and must be approved through the
    local FastAPI approval endpoint before execution.
    """

    if _service is None:
        return '{"ok": false, "error": "askdb_mcp service is not initialized."}'
    return _service.ask_database_json(question)


def build_service() -> tuple[AskDBService, uvicorn.Server]:
    settings = load_settings()
    executor = SQLiteExecutor(settings.sqlite_db_path, max_rows=settings.max_rows)
    executor.ensure_available()
    store = PendingWriteStore(settings.pending_ttl_seconds)
    service = AskDBService(
        schema_service=SchemaService(settings.sqlite_db_path),
        sql_generator=OpenAISqlGenerator(settings),
        executor=executor,
        pending_store=store,
    )
    api = create_app(settings, store, executor)
    config = uvicorn.Config(api, host=settings.host, port=settings.port, log_level="info")
    return service, uvicorn.Server(config)


def main() -> None:
    global _service
    _service, api_server = build_service()
    thread = threading.Thread(target=api_server.run, name="askdb-fastapi", daemon=True)
    thread.start()
    mcp.run()


if __name__ == "__main__":
    main()

