"""FastAPI approval API."""

from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException, status

from askdb_mcp.config import Settings
from askdb_mcp.pending_store import PendingWriteStore
from askdb_mcp.sqlite_executor import SQLiteExecutor


def create_app(settings: Settings, store: PendingWriteStore, executor: SQLiteExecutor) -> FastAPI:
    app = FastAPI(title="askdb_mcp approval API", version="0.1.0")

    def require_api_key(x_askdb_key: str | None = Header(default=None, alias="X-AskDB-Key")) -> None:
        if x_askdb_key != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing X-AskDB-Key header.",
            )

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "ok": True,
            "database": str(settings.sqlite_db_path),
            "pending_writes": len(store.list()),
        }

    @app.get("/pending-writes", dependencies=[Depends(require_api_key)])
    def list_pending_writes() -> dict[str, object]:
        items = [pending.to_dict() for pending in store.list()]
        return {"count": len(items), "items": items}

    @app.get("/pending-writes/{pending_id}", dependencies=[Depends(require_api_key)])
    def get_pending_write(pending_id: str) -> dict[str, object]:
        pending = store.get(pending_id)
        if pending is None:
            raise HTTPException(status_code=404, detail="Pending write not found.")
        return pending.to_dict()

    @app.post("/pending-writes/{pending_id}/approve", dependencies=[Depends(require_api_key)])
    def approve_pending_write(pending_id: str) -> dict[str, object]:
        try:
            pending = store.approve(pending_id)
            result = executor.execute(pending.sql)
            executed = store.mark_executed(pending.id, result)
            return executed.to_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/pending-writes/{pending_id}/reject", dependencies=[Depends(require_api_key)])
    def reject_pending_write(pending_id: str) -> dict[str, object]:
        try:
            return store.reject(pending_id).to_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return app

