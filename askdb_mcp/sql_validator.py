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
    "truncate",
    "vacuum",
}
READ_KEYWORDS = {"select", "with"}
WRITE_KEYWORDS = {"insert", "update", "delete"}

# Quoted strings and identifiers, so keyword checks never look inside them.
_QUOTED = re.compile(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|`(?:[^`]|``)*`|\[[^\]]*\]")
# REPLACE INTO / INSERT OR REPLACE are blocked, but the replace() string function is fine.
_REPLACE_STATEMENT = re.compile(r"\breplace\b(?!\s*\()")


class SqlValidationError(ValueError):
    """Raised when generated SQL is unsafe or unsupported."""


def classify_sql(sql: str) -> SqlOperation:
    code = _strip_quoted(_normalize(sql)).lower()
    first = code.split(None, 1)[0] if code.split() else ""
    if first in WRITE_KEYWORDS:
        return SqlOperation.WRITE
    if first == "with":
        # A CTE can front a write: WITH x AS (...) DELETE FROM ...
        top_level = set(re.findall(r"[a-z_]+", _top_level_text(code)))
        return SqlOperation.WRITE if top_level & WRITE_KEYWORDS else SqlOperation.READ
    if first in READ_KEYWORDS:
        return SqlOperation.READ
    return SqlOperation.UNSUPPORTED


def validate_sql(sql: str) -> SqlOperation:
    """Validate SQL and return its operation class."""

    normalized = _normalize(sql)
    if not normalized:
        raise SqlValidationError("Generated SQL was empty.")
    code = _strip_quoted(normalized)
    if "--" in code or "/*" in code or "*/" in code:
        raise SqlValidationError("SQL comments are not allowed in generated statements.")
    if not sqlite3.complete_statement(normalized + ";"):
        raise SqlValidationError("Generated SQL is incomplete.")
    if ";" in code:
        raise SqlValidationError("Only one SQL statement is allowed.")

    lowered = code.lower()
    blocked = set(re.findall(r"[a-z_]+", lowered)) & BLOCKED_KEYWORDS
    if _REPLACE_STATEMENT.search(lowered):
        blocked.add("replace")
    if blocked:
        raise SqlValidationError(f"Blocked SQL keyword(s): {', '.join(sorted(blocked))}.")

    operation = classify_sql(normalized)
    if operation == SqlOperation.UNSUPPORTED:
        raise SqlValidationError("Only SELECT, WITH, INSERT, UPDATE, and DELETE are supported.")
    return operation


def _normalize(sql: str) -> str:
    return sql.strip().rstrip(";").strip()


def _strip_quoted(sql: str) -> str:
    return _QUOTED.sub(" q ", sql)


def _top_level_text(code: str) -> str:
    """Return only the text outside parentheses."""

    depth = 0
    chars: list[str] = []
    for ch in code:
        if ch == "(":
            depth += 1
            chars.append(" ")
        elif ch == ")":
            depth = max(depth - 1, 0)
            chars.append(" ")
        else:
            chars.append(ch if depth == 0 else " ")
    return "".join(chars)
