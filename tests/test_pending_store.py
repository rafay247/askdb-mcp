from datetime import datetime, timedelta, timezone

import pytest

from askdb_mcp.models import PendingStatus, QueryResult
from askdb_mcp.pending_store import PendingWriteStore


def _create(store):
    return store.create(sql="DELETE FROM t", question="q", explanation="e", risk_summary="r")


def test_approve_only_once():
    store = PendingWriteStore(ttl_seconds=60)
    pending = _create(store)
    store.approve(pending.id)
    with pytest.raises(ValueError):
        store.approve(pending.id)


def test_unknown_id_raises_key_error():
    with pytest.raises(KeyError):
        PendingWriteStore(ttl_seconds=60).reject("missing")


def test_expired_cannot_be_approved():
    store = PendingWriteStore(ttl_seconds=60)
    pending = _create(store)
    pending.created_at = datetime.now(timezone.utc) - timedelta(seconds=61)
    with pytest.raises(ValueError):
        store.approve(pending.id)
    assert store.get(pending.id).status == PendingStatus.EXPIRED


def test_mark_failed_and_executed():
    store = PendingWriteStore(ttl_seconds=60)
    first, second = _create(store), _create(store)
    store.approve(first.id)
    assert store.mark_failed(first.id, "boom").error == "boom"
    store.approve(second.id)
    result = QueryResult(sql="x", columns=[], rows=[], row_count=0, affected_rows=1)
    assert store.mark_executed(second.id, result).status == PendingStatus.EXECUTED


def test_prunes_old_finished_items():
    store = PendingWriteStore(ttl_seconds=60)
    pending = _create(store)
    store.reject(pending.id)
    pending.created_at = datetime.now(timezone.utc) - timedelta(seconds=121)
    assert store.get(pending.id) is None
