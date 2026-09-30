"""Application service that coordinates NL-to-SQL, validation, and execution."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Protocol

from askdb_mcp.models import GeneratedSql, PendingStatus, PendingWrite, SqlOperation
from askdb_mcp.pending_store import PendingWriteStore
from askdb_mcp.schema_service import SchemaService
from askdb_mcp.sql_validator import SqlValidationError, validate_sql
from askdb_mcp.sqlite_executor import SQLiteExecutor


class SqlGenerator(Protocol):
    def generate(self, question: str, schema_context: str) -> GeneratedSql: ...


class AskDBService:
    def __init__(
        self,
        *,
        schema_service: SchemaService,
        sql_generator: SqlGenerator,
        executor: SQLiteExecutor,
        pending_store: PendingWriteStore,
    ) -> None:
        self.schema_service = schema_service
        self.sql_generator = sql_generator
        self.executor = executor
        self.pending_store = pending_store

    def ask_database(self, question: str) -> dict[str, Any]:
        if not question.strip():
            return {"ok": False, "error": "Question cannot be empty."}

        schema_context = self.schema_service.format_for_prompt()
        try:
            generated = self.sql_generator.generate(question, schema_context)
        except Exception as exc:
            return {
                "ok": False,
                "error": "Could not generate SQL with OpenAI.",
                "detail": str(exc),
            }

        if generated.operation == SqlOperation.UNSUPPORTED and not generated.sql.strip():
            return {
                "ok": False,
                "error": "This request cannot be answered with a supported SQL statement.",
                "explanation": generated.explanation,
            }

        try:
            operation = validate_sql(generated.sql)
        except SqlValidationError as exc:
            return {
                "ok": False,
                "error": str(exc),
                "generated_sql": generated.sql,
                "explanation": generated.explanation,
            }

        if generated.operation != operation and generated.operation != SqlOperation.UNSUPPORTED:
            return {
                "ok": False,
                "error": "Generated operation did not match validated SQL operation.",
                "generated_operation": generated.operation.value,
                "validated_operation": operation.value,
                "generated_sql": generated.sql,
            }

        if operation == SqlOperation.READ:
            try:
                result = self.executor.execute(generated.sql)
            except (sqlite3.Error, SqlValidationError) as exc:
                return {
                    "ok": False,
                    "error": f"SQLite could not run the generated query: {exc}",
                    "generated_sql": generated.sql,
                    "explanation": generated.explanation,
                }
            return {
                "ok": True,
                "status": "executed",
                "operation": operation.value,
                "sql": result.sql,
                "explanation": generated.explanation,
                "columns": result.columns,
                "rows": result.rows,
                "row_count": result.row_count,
                "truncated": result.truncated,
            }

        pending = self.pending_store.create(
            sql=generated.sql,
            question=question,
            explanation=generated.explanation,
            risk_summary=generated.risk_summary,
        )
        return {
            "ok": True,
            "status": "pending_approval",
            "operation": operation.value,
            "pending_write_id": pending.id,
            "sql": pending.sql,
            "explanation": pending.explanation,
            "risk_summary": pending.risk_summary,
            "approval": {
                "list": "GET /pending-writes",
                "approve": f"POST /pending-writes/{pending.id}/approve",
                "reject": f"POST /pending-writes/{pending.id}/reject",
                "auth_header": "X-AskDB-Key",
            },
        }

    def ask_database_json(self, question: str) -> str:
        return json.dumps(self.ask_database(question), indent=2, default=str)

    def describe_schema(self) -> dict[str, Any]:
        return self.schema_service.describe_schema()

    def list_pending(self) -> list[PendingWrite]:
        return [item for item in self.pending_store.list() if item.status == PendingStatus.PENDING]

    def get_pending(self, pending_id: str) -> PendingWrite | None:
        return self.pending_store.get(pending_id)

    def approve_write(self, pending_id: str) -> PendingWrite:
        """Execute a pending write.

        Raises KeyError if the proposal is unknown and ValueError if it is no longer
        pending. Execution failures are recorded on the proposal with status ``failed``.
        """

        pending = self.pending_store.approve(pending_id)
        try:
            result = self.executor.execute(pending.sql)
        except (sqlite3.Error, SqlValidationError) as exc:
            return self.pending_store.mark_failed(pending.id, str(exc))
        return self.pending_store.mark_executed(pending.id, result)

    def reject_write(self, pending_id: str) -> PendingWrite:
        return self.pending_store.reject(pending_id)
