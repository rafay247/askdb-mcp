import sqlite3

import pytest

from askdb_mcp.sqlite_executor import SQLiteExecutor


def test_read_returns_rows(demo_db):
    result = SQLiteExecutor(demo_db).execute("SELECT id, name FROM customers ORDER BY id")
    assert result.columns == ["id", "name"]
    assert result.row_count == 6
    assert result.rows[0] == {"id": 1, "name": "Olivia Bennett"}
    assert result.truncated is False


def test_read_reports_truncation(demo_db):
    result = SQLiteExecutor(demo_db, max_rows=2).execute("SELECT id FROM customers")
    assert result.row_count == 2
    assert result.truncated is True


def test_write_commits(demo_db):
    executor = SQLiteExecutor(demo_db)
    result = executor.execute("UPDATE customers SET city = 'Paris' WHERE id = 1")
    assert result.affected_rows == 1
    rows = executor.execute("SELECT city FROM customers WHERE id = 1").rows
    assert rows == [{"city": "Paris"}]


def test_read_connection_cannot_write(demo_db):
    executor = SQLiteExecutor(demo_db)
    with pytest.raises(sqlite3.Error):
        executor._execute_read("DELETE FROM customers")
    assert executor.execute("SELECT count(*) AS n FROM customers").rows == [{"n": 6}]


def test_write_enforces_foreign_keys(demo_db):
    executor = SQLiteExecutor(demo_db)
    with pytest.raises(sqlite3.IntegrityError):
        executor.execute("DELETE FROM customers WHERE id = 1")
    assert executor.execute("SELECT count(*) AS n FROM customers").rows == [{"n": 6}]


def test_write_authorizer_blocks_schema_changes(demo_db):
    executor = SQLiteExecutor(demo_db)
    with pytest.raises(sqlite3.DatabaseError):
        executor._execute_write("DROP TABLE orders")
