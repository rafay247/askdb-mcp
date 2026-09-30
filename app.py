"""Vercel entrypoint: exposes the AskDB web UI, approval API, and /mcp endpoint."""

from askdb_mcp.web import create_hosted_app


app = create_hosted_app()
