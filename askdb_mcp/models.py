"""Shared data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SqlOperation(str, Enum):
    READ = "read"
    WRITE = "write"
    UNSUPPORTED = "unsupported"


class PendingStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


@dataclass(frozen=True)
class GeneratedSql:
    sql: str
    operation: SqlOperation
    explanation: str
    risk_summary: str


@dataclass(frozen=True)
class QueryResult:
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    affected_rows: int


@dataclass
class PendingWrite:
    id: str
    sql: str
    question: str
    explanation: str
    risk_summary: str
    status: PendingStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    executed_at: datetime | None = None
    result: QueryResult | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["executed_at"] = self.executed_at.isoformat() if self.executed_at else None
        return data

