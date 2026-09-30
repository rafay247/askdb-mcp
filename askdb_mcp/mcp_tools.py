"""MCP tool definitions shared by the stdio and HTTP transports."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from askdb_mcp.service import AskDBService


def build_mcp(service: AskDBService) -> FastMCP:
    mcp = FastMCP("askdb_mcp")

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
    def askdb_ask_database(question: str) -> str:
        """Ask the configured SQLite database a natural language question.

        Read-only SQL is executed immediately after validation. INSERT, UPDATE, and
        DELETE statements return a pending write ID and must be approved by a human
        through the AskDB approval API or browser UI before execution.
        """

        return service.ask_database_json(question)

    @mcp.tool(
        name="askdb_describe_schema",
        annotations={"title": "Describe SQLite Schema", "readOnlyHint": True, "openWorldHint": False},
    )
    def askdb_describe_schema() -> str:
        """Return the tables, columns, and foreign keys of the configured database."""

        return json.dumps(service.describe_schema(), indent=2)

    @mcp.tool(
        name="askdb_get_pending_write",
        annotations={"title": "Get Pending Write Status", "readOnlyHint": True, "openWorldHint": False},
    )
    def askdb_get_pending_write(pending_write_id: str) -> str:
        """Check whether a proposed write is still pending, executed, failed, rejected, or expired."""

        pending = service.get_pending(pending_write_id)
        if pending is None:
            return json.dumps({"ok": False, "error": f"Pending write not found: {pending_write_id}"})
        return json.dumps({"ok": True, **pending.to_dict()}, indent=2, default=str)

    return mcp
