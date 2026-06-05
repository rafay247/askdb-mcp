"""SQLite execution helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from askdb_mcp.models import QueryResult, SqlOperation
from askdb_mcp.sql_validator import validate_sql


class SQLiteExecutor:
    def __init__(self, db_path: Path, max_rows: int = 100) -> None:
        self.db_path = db_path
        self.max_rows = max_rows

    def ensure_available(self) -> None:
        if not self.db_path.exists():
            raise RuntimeError(f"SQLite database does not exist: {self.db_path}")

    def execute(self, sql: str) -> QueryResult:
        operation = validate_sql(sql)
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(sql)
            if operation == SqlOperation.READ:
                rows = cursor.fetchmany(self.max_rows)
                columns = [column[0] for column in cursor.description or []]
                mapped_rows: list[dict[str, Any]] = [dict(row) for row in rows]
                return QueryResult(
                    sql=sql,
                    columns=columns,
                    rows=mapped_rows,
                    row_count=len(mapped_rows),
                    affected_rows=0,
                )

            connection.commit()
            return QueryResult(
                sql=sql,
                columns=[],
                rows=[],
                row_count=0,
                affected_rows=cursor.rowcount,
            )

