import pytest

from askdb_mcp.models import SqlOperation
from askdb_mcp.sql_validator import SqlValidationError, validate_sql


def test_validate_read_select():
    assert validate_sql("SELECT * FROM users") == SqlOperation.READ


def test_validate_write_update():
    assert validate_sql("UPDATE users SET name = 'Ada' WHERE id = 1") == SqlOperation.WRITE


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE users",
        "SELECT * FROM users; DELETE FROM users",
        "PRAGMA journal_mode = WAL",
        "SELECT * FROM users -- hidden",
        "CREATE TABLE x (id integer)",
    ],
)
def test_rejects_unsafe_sql(sql):
    with pytest.raises(SqlValidationError):
        validate_sql(sql)

