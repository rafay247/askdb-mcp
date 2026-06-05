from datetime import datetime, timedelta, timezone

import pytest

from askdb_mcp.models import PendingStatus
from askdb_mcp.pending_store import PendingWriteStore


def test_pending_write_lifecycle():
    store = PendingWriteStore(ttl_seconds=3600)
    pending = store.create(
        sql="UPDATE users SET name = 'Ada' WHERE id = 1",
        question="Rename user 1",
        explanation="Updates one row",
        risk_summary="Changes user name",
    )

    assert store.get(pending.id).status == PendingStatus.PENDING
    assert store.approve(pending.id).status == PendingStatus.APPROVED

    with pytest.raises(ValueError):
        store.reject(pending.id)


def test_pending_write_expires():
    store = PendingWriteStore(ttl_seconds=1)
    pending = store.create(
        sql="DELETE FROM users WHERE id = 1",
        question="Delete user 1",
        explanation="Deletes one row",
        risk_summary="Removes data",
    )
    pending.created_at = datetime.now(timezone.utc) - timedelta(seconds=2)

    assert store.get(pending.id).status == PendingStatus.EXPIRED

