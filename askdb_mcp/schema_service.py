"""SQLite schema introspection."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class SchemaService:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def describe_schema(self) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            tables = self._list_tables(connection)
            return {"tables": [self._describe_table(connection, table) for table in tables]}

    def format_for_prompt(self) -> str:
        schema = self.describe_schema()
        lines: list[str] = []
        for table in schema["tables"]:
            lines.append(f"Table: {table['name']}")
            for column in table["columns"]:
                pk = " primary key" if column["primary_key"] else ""
                nullable = "" if column["not_null"] else " nullable"
                lines.append(f"- {column['name']} {column['type']}{pk}{nullable}")
            if table["foreign_keys"]:
                lines.append("Foreign keys:")
                for key in table["foreign_keys"]:
                    lines.append(
                        f"- {key['from']} -> {key['references_table']}.{key['references_column']}"
                    )
        return "\n".join(lines)

    def _list_tables(self, connection: sqlite3.Connection) -> list[str]:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        return [row["name"] for row in rows]

    def _describe_table(self, connection: sqlite3.Connection, table_name: str) -> dict[str, Any]:
        columns = [
            {
                "name": row["name"],
                "type": row["type"],
                "not_null": bool(row["notnull"]),
                "default": row["dflt_value"],
                "primary_key": bool(row["pk"]),
            }
            for row in connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        ]
        foreign_keys = [
            {
                "from": row["from"],
                "references_table": row["table"],
                "references_column": row["to"],
            }
            for row in connection.execute(f'PRAGMA foreign_key_list("{table_name}")').fetchall()
        ]
        return {"name": table_name, "columns": columns, "foreign_keys": foreign_keys}

