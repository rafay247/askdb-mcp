"""SQLite SQL validation and operation classification."""

from __future__ import annotations

import re
import sqlite3

from askdb_mcp.models import SqlOperation


BLOCKED_KEYWORDS = {
    "alter",
    "attach",
    "create",
    "detach",
    "drop",
    "pragma",
    "reindex",
    "replace",
    "truncate",
    "vacuum",
}
READ_KEYWORDS = {"select", "with"}
WRITE_KEYWORDS = {"insert", "update", "delete"}


class SqlValidationError(ValueError):
    """Raised when generated SQL is unsafe or unsupported."""


def classify_sql(sql: str) -> SqlOperation:
    normalized = _normalize(sql)
    first = normalized.split(" ", 1)[0].lower()
    if first in READ_KEYWORDS:
        return SqlOperation.READ
    if first in WRITE_KEYWORDS:
        return SqlOperation.WRITE
    return SqlOperation.UNSUPPORTED


def validate_sql(sql: str) -> SqlOperation:
    """Validate SQL and return its operation class."""

    normalized = _normalize(sql)
    if not normalized:
        raise SqlValidationError("Generated SQL was empty.")
    if "--" in normalized or "/*" in normalized or "*/" in normalized:
        raise SqlValidationError("SQL comments are not allowed in generated statements.")
    if not sqlite3.complete_statement(normalized + ";"):
        raise SqlValidationError("Generated SQL is incomplete.")
    if _has_multiple_statements(normalized):
        raise SqlValidationError("Only one SQL statement is allowed.")

    tokens = set(re.findall(r"[A-Za-z_]+", normalized.lower()))
    blocked = sorted(tokens.intersection(BLOCKED_KEYWORDS))
    if blocked:
        raise SqlValidationError(f"Blocked SQL keyword(s): {', '.join(blocked)}.")

    operation = classify_sql(normalized)
    if operation == SqlOperation.UNSUPPORTED:
        raise SqlValidationError("Only SELECT, WITH, INSERT, UPDATE, and DELETE are supported.")
    return operation


def _normalize(sql: str) -> str:
    return sql.strip().rstrip(";").strip()


def _has_multiple_statements(sql: str) -> bool:
    stripped = sql.strip()
    without_final = stripped[:-1] if stripped.endswith(";") else stripped
    return ";" in without_final

