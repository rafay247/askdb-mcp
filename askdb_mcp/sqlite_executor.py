"""SQLite execution helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from askdb_mcp.models import QueryResult, SqlOperation
from askdb_mcp.sql_validator import validate_sql


_READ_ACTIONS = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_READ,
    sqlite3.SQLITE_FUNCTION,
    sqlite3.SQLITE_RECURSIVE,
}
_WRITE_ACTIONS = _READ_ACTIONS | {
    sqlite3.SQLITE_INSERT,
    sqlite3.SQLITE_UPDATE,
    sqlite3.SQLITE_DELETE,
    sqlite3.SQLITE_TRANSACTION,
}


class SQLiteExecutor:
    def __init__(self, db_path: Path, max_rows: int = 100) -> None:
        self.db_path = db_path
        self.max_rows = max_rows

    def ensure_available(self) -> None:
        if not self.db_path.exists():
            raise RuntimeError(f"SQLite database does not exist: {self.db_path}")

    def execute(self, sql: str) -> QueryResult:
        operation = validate_sql(sql)
        if operation == SqlOperation.READ:
            return self._execute_read(sql)
        return self._execute_write(sql)

    def _execute_read(self, sql: str) -> QueryResult:
        # Read-only at the file level too, so a misclassified write can never commit.
        uri = f"{self.db_path.resolve().as_uri()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        try:
            connection.row_factory = sqlite3.Row
            connection.set_authorizer(_authorizer(_READ_ACTIONS))
            cursor = connection.execute(sql)
            rows = cursor.fetchmany(self.max_rows + 1)
            columns = [column[0] for column in cursor.description or []]
            truncated = len(rows) > self.max_rows
            mapped_rows: list[dict[str, Any]] = [dict(row) for row in rows[: self.max_rows]]
            return QueryResult(
                sql=sql,
                columns=columns,
                rows=mapped_rows,
                row_count=len(mapped_rows),
                affected_rows=0,
                truncated=truncated,
            )
        finally:
            connection.close()

    def _execute_write(self, sql: str) -> QueryResult:
        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.set_authorizer(_authorizer(_WRITE_ACTIONS))
            try:
                cursor = connection.execute(sql)
                connection.commit()
            except sqlite3.Error:
                connection.rollback()
                raise
            return QueryResult(
                sql=sql,
                columns=[],
                rows=[],
                row_count=0,
                affected_rows=cursor.rowcount,
            )
        finally:
            connection.close()


def _authorizer(allowed: set[int]):
    def check(action: int, *_: object) -> int:
        return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY

    return check
