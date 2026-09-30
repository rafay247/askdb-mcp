"""MCP stdio server plus local FastAPI approval server."""

from __future__ import annotations

import threading

import uvicorn

from askdb_mcp.api import create_app
from askdb_mcp.config import load_settings
from askdb_mcp.mcp_tools import build_mcp
from askdb_mcp.runtime import build_components


def main() -> None:
    components = build_components(load_settings())
    settings = components.settings
    api = create_app(settings, components.service)
    config = uvicorn.Config(api, host=settings.host, port=settings.port, log_level="info")
    api_server = uvicorn.Server(config)
    thread = threading.Thread(target=api_server.run, name="askdb-fastapi", daemon=True)
    thread.start()
    build_mcp(components.service).run()


if __name__ == "__main__":
    main()
