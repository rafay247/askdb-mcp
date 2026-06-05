"""Application service that coordinates NL-to-SQL, validation, and execution."""

from __future__ import annotations

import json
from typing import Any

from askdb_mcp.models import GeneratedSql, SqlOperation
from askdb_mcp.openai_sql_generator import OpenAISqlGenerator
from askdb_mcp.pending_store import PendingWriteStore
from askdb_mcp.schema_service import SchemaService
from askdb_mcp.sql_validator import SqlValidationError, validate_sql
from askdb_mcp.sqlite_executor import SQLiteExecutor


class AskDBService:
    def __init__(
        self,
        *,
        schema_service: SchemaService,
        sql_generator: OpenAISqlGenerator,
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
        generated = self.sql_generator.generate(question, schema_context)
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
            result = self.executor.execute(generated.sql)
            return {
                "ok": True,
                "status": "executed",
                "operation": operation.value,
                "sql": result.sql,
                "explanation": generated.explanation,
                "columns": result.columns,
                "rows": result.rows,
                "row_count": result.row_count,
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

