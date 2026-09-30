import pytest

from askdb_mcp.models import SqlOperation
from askdb_mcp.sql_validator import SqlValidationError, classify_sql, validate_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM customers",
        "select name from customers;",
        "WITH c AS (SELECT * FROM customers) SELECT * FROM c",
        "SELECT * FROM customers WHERE name = 'Drop Create'",
        "SELECT * FROM customers WHERE name LIKE '%--%'",
        "SELECT * FROM customers WHERE city = 'a;b'",
        "SELECT replace(name, 'a', 'b') FROM customers",
        'SELECT "update" FROM customers',
    ],
)
def test_allows_reads(sql):
    assert validate_sql(sql) == SqlOperation.READ


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO customers (name) VALUES ('Alex')",
        "UPDATE customers SET city = 'Paris' WHERE id = 1",
        "DELETE FROM customers WHERE id = 1",
        "WITH old AS (SELECT id FROM customers) DELETE FROM customers WHERE id IN (SELECT id FROM old)",
        "WITH x AS (SELECT 1) UPDATE customers SET city = 'Oslo'",
    ],
)
def test_classifies_writes(sql):
    assert validate_sql(sql) == SqlOperation.WRITE


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "DROP TABLE customers",
        "SELECT 1; DROP TABLE customers",
        "SELECT * FROM customers -- comment",
        "SELECT /* x */ 1",
        "PRAGMA table_info(customers)",
        "ATTACH DATABASE 'x.db' AS x",
        "REPLACE INTO customers (id, name) VALUES (1, 'x')",
        "INSERT OR REPLACE INTO customers (id, name) VALUES (1, 'x')",
        "CREATE TABLE t (id INTEGER)",
        "SELECT * FROM customers WHERE name = 'unterminated",
        "EXPLAIN SELECT 1",
    ],
)
def test_rejects_unsafe_or_unsupported(sql):
    with pytest.raises(SqlValidationError):
        validate_sql(sql)


def test_classify_unknown_is_unsupported():
    assert classify_sql("VACUUM") == SqlOperation.UNSUPPORTED
