from askdb_mcp.models import GeneratedSql, PendingStatus, SqlOperation
from askdb_mcp.pending_store import PendingWriteStore
from askdb_mcp.schema_service import SchemaService
from askdb_mcp.service import AskDBService
from askdb_mcp.sqlite_executor import SQLiteExecutor


class FakeGenerator:
    def __init__(self, sql, operation, explanation="x"):
        self.result = GeneratedSql(sql=sql, operation=operation, explanation=explanation, risk_summary="r")

    def generate(self, question, schema_context):
        return self.result


class FailingGenerator:
    def generate(self, question, schema_context):
        raise RuntimeError("no key")


def make_service(db, generator):
    return AskDBService(
        schema_service=SchemaService(db),
        sql_generator=generator,
        executor=SQLiteExecutor(db),
        pending_store=PendingWriteStore(ttl_seconds=60),
    )


def count_customers(db):
    return SQLiteExecutor(db).execute("SELECT count(*) AS n FROM customers").rows[0]["n"]


def test_read_executes_immediately(demo_db):
    service = make_service(demo_db, FakeGenerator("SELECT name FROM customers", SqlOperation.READ))
    response = service.ask_database("names")
    assert response["status"] == "executed"
    assert response["row_count"] == 6


def test_write_waits_for_approval_then_executes(demo_db):
    sql = "INSERT INTO customers (name, email, city) VALUES ('Alex', 'a@x.io', 'Paris')"
    service = make_service(demo_db, FakeGenerator(sql, SqlOperation.WRITE))
    response = service.ask_database("add alex")
    assert response["status"] == "pending_approval"
    assert count_customers(demo_db) == 6

    approved = service.approve_write(response["pending_write_id"])
    assert approved.status == PendingStatus.EXECUTED
    assert approved.result.affected_rows == 1
    assert count_customers(demo_db) == 7


def test_rejected_write_never_runs(demo_db):
    service = make_service(demo_db, FakeGenerator("DELETE FROM orders", SqlOperation.WRITE))
    pending_id = service.ask_database("clear orders")["pending_write_id"]
    assert service.reject_write(pending_id).status == PendingStatus.REJECTED
    assert service.list_pending() == []


def test_cte_write_labelled_read_is_not_executed(demo_db):
    sql = "WITH x AS (SELECT 1) DELETE FROM orders"
    service = make_service(demo_db, FakeGenerator(sql, SqlOperation.READ))
    response = service.ask_database("sneaky")
    assert response["ok"] is False
    assert SQLiteExecutor(demo_db).execute("SELECT count(*) AS n FROM orders").rows[0]["n"] == 6


def test_failed_approval_is_recorded(demo_db):
    service = make_service(demo_db, FakeGenerator("DELETE FROM customers WHERE id = 1", SqlOperation.WRITE))
    pending_id = service.ask_database("remove olivia")["pending_write_id"]
    failed = service.approve_write(pending_id)
    assert failed.status == PendingStatus.FAILED
    assert "FOREIGN KEY" in failed.error
    assert count_customers(demo_db) == 6


def test_bad_generated_sql_returns_error(demo_db):
    service = make_service(demo_db, FakeGenerator("SELECT nope FROM customers", SqlOperation.READ))
    response = service.ask_database("bad")
    assert response["ok"] is False
    assert "no such column" in response["error"]


def test_unsupported_request(demo_db):
    service = make_service(demo_db, FakeGenerator("", SqlOperation.UNSUPPORTED, "Cannot drop tables."))
    response = service.ask_database("drop everything")
    assert response["ok"] is False
    assert response["explanation"] == "Cannot drop tables."


def test_generator_error_and_empty_question(demo_db):
    service = make_service(demo_db, FailingGenerator())
    assert service.ask_database("   ")["error"] == "Question cannot be empty."
    assert service.ask_database("hi")["detail"] == "no key"
