import sqlite3

from askdb_mcp.models import GeneratedSql, SqlOperation
from askdb_mcp.pending_store import PendingWriteStore
from askdb_mcp.schema_service import SchemaService
from askdb_mcp.service import AskDBService
from askdb_mcp.sqlite_executor import SQLiteExecutor


class FakeGenerator:
    def __init__(self, generated):
        self.generated = generated

    def generate(self, question, schema_context):
        return self.generated


def _make_db(tmp_path):
    db_path = tmp_path / "test.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE users (id integer primary key, name text)")
        connection.execute("INSERT INTO users (name) VALUES ('Ada')")
    return db_path


def test_service_executes_reads(tmp_path):
    db_path = _make_db(tmp_path)
    service = AskDBService(
        schema_service=SchemaService(db_path),
        sql_generator=FakeGenerator(
            GeneratedSql(
                sql="SELECT name FROM users",
                operation=SqlOperation.READ,
                explanation="Reads user names",
                risk_summary="No write risk",
            )
        ),
        executor=SQLiteExecutor(db_path),
        pending_store=PendingWriteStore(ttl_seconds=3600),
    )

    response = service.ask_database("show users")

    assert response["ok"] is True
    assert response["status"] == "executed"
    assert response["rows"][0]["name"] == "Ada"


def test_service_defers_writes(tmp_path):
    db_path = _make_db(tmp_path)
    service = AskDBService(
        schema_service=SchemaService(db_path),
        sql_generator=FakeGenerator(
            GeneratedSql(
                sql="UPDATE users SET name = 'Grace' WHERE id = 1",
                operation=SqlOperation.WRITE,
                explanation="Renames a user",
                risk_summary="Modifies one row",
            )
        ),
        executor=SQLiteExecutor(db_path),
        pending_store=PendingWriteStore(ttl_seconds=3600),
    )

    response = service.ask_database("rename user")

    assert response["ok"] is True
    assert response["status"] == "pending_approval"
    assert "pending_write_id" in response

