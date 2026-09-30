"""ASGI entrypoint for hosted deployments such as Vercel (no stdio MCP process)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from askdb_mcp.api import create_app
from askdb_mcp.config import load_settings
from askdb_mcp.runtime import build_components


def create_hosted_app() -> FastAPI:
    try:
        components = build_components(load_settings())
    except Exception as exc:
        return _config_error_app(str(exc))
    return create_app(components.settings, components.service)


def _config_error_app(message: str) -> FastAPI:
    """Serve a readable 503 instead of crashing the function on bad configuration."""

    app = FastAPI(title="AskDB (misconfigured)")

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def misconfigured(path: str, request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "ok": False,
                "error": "AskDB is not configured.",
                "detail": message,
                "hint": "Set ASKDB_API_KEY (12+ chars) or ASKDB_AUTH_MODE=optional, and optionally OPENAI_API_KEY in the project's environment variables, then redeploy.",
            },
            status_code=503,
        )

    return app
