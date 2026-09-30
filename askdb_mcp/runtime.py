"""Wire settings into the service objects used by every entrypoint."""

from __future__ import annotations

from dataclasses import dataclass

from askdb_mcp.config import Settings
from askdb_mcp.demo_db import create_demo_database
from askdb_mcp.openai_sql_generator import OpenAISqlGenerator
from askdb_mcp.pending_store import PendingWriteStore
from askdb_mcp.schema_service import SchemaService
from askdb_mcp.service import AskDBService
from askdb_mcp.sqlite_executor import SQLiteExecutor


@dataclass(frozen=True)
class Components:
    settings: Settings
    service: AskDBService


def build_components(settings: Settings) -> Components:
    if settings.seed_demo_db:
        create_demo_database(settings.sqlite_db_path)
    executor = SQLiteExecutor(settings.sqlite_db_path, max_rows=settings.max_rows)
    executor.ensure_available()
    service = AskDBService(
        schema_service=SchemaService(settings.sqlite_db_path),
        sql_generator=OpenAISqlGenerator(settings),
        executor=executor,
        pending_store=PendingWriteStore(settings.pending_ttl_seconds),
    )
    return Components(settings=settings, service=service)
