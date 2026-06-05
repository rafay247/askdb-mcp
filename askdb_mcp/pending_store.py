"""In-memory pending write proposal store."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Lock
from uuid import uuid4

from askdb_mcp.models import PendingStatus, PendingWrite, QueryResult


class PendingWriteStore:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl = timedelta(seconds=ttl_seconds)
        self._items: dict[str, PendingWrite] = {}
        self._lock = Lock()

    def create(self, *, sql: str, question: str, explanation: str, risk_summary: str) -> PendingWrite:
        with self._lock:
            pending = PendingWrite(
                id=uuid4().hex,
                sql=sql,
                question=question,
                explanation=explanation,
                risk_summary=risk_summary,
                status=PendingStatus.PENDING,
            )
            self._items[pending.id] = pending
            return pending

    def list(self) -> list[PendingWrite]:
        with self._lock:
            self._expire_old_locked()
            return list(self._items.values())

    def get(self, pending_id: str) -> PendingWrite | None:
        with self._lock:
            self._expire_old_locked()
            return self._items.get(pending_id)

    def approve(self, pending_id: str) -> PendingWrite:
        with self._lock:
            self._expire_old_locked()
            pending = self._require_pending_locked(pending_id)
            pending.status = PendingStatus.APPROVED
            return pending

    def reject(self, pending_id: str) -> PendingWrite:
        with self._lock:
            self._expire_old_locked()
            pending = self._require_pending_locked(pending_id)
            pending.status = PendingStatus.REJECTED
            return pending

    def mark_executed(self, pending_id: str, result: QueryResult) -> PendingWrite:
        with self._lock:
            pending = self._items[pending_id]
            pending.status = PendingStatus.EXECUTED
            pending.executed_at = datetime.now(timezone.utc)
            pending.result = result
            return pending

    def _require_pending_locked(self, pending_id: str) -> PendingWrite:
        pending = self._items.get(pending_id)
        if pending is None:
            raise KeyError(f"Pending write not found: {pending_id}")
        if pending.status != PendingStatus.PENDING:
            raise ValueError(f"Pending write is not approvable because status is {pending.status.value}.")
        return pending

    def _expire_old_locked(self) -> None:
        now = datetime.now(timezone.utc)
        for pending in self._items.values():
            if pending.status == PendingStatus.PENDING and now - pending.created_at > self.ttl:
                pending.status = PendingStatus.EXPIRED

