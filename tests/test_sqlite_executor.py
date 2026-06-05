import sqlite3

from askdb_mcp.sqlite_executor import SQLiteExecutor


def test_executor_returns_rows(tmp_path):
    db_path = tmp_path / "test.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE users (id integer primary key, name text)")
        connection.execute("INSERT INTO users (name) VALUES ('Ada')")

    result = SQLiteExecutor(db_path).execute("SELECT id, name FROM users")

    assert result.columns == ["id", "name"]
    assert result.row_count == 1
    assert result.rows[0]["name"] == "Ada"


def test_executor_commits_writes(tmp_path):
    db_path = tmp_path / "test.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE users (id integer primary key, name text)")

    result = SQLiteExecutor(db_path).execute("INSERT INTO users (name) VALUES ('Grace')")

    assert result.affected_rows == 1
    with sqlite3.connect(db_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    assert count == 1

