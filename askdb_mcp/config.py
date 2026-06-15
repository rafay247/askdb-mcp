"""Runtime configuration for askdb_mcp."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    sqlite_db_path: Path
    api_key: str
    openai_model: str = "gpt-4o-mini"
    host: str = "127.0.0.1"
    port: int = 8765
    pending_ttl_seconds: int = 3600
    max_rows: int = 100


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable {name}.")
    return value


def _load_dotenv(path: Path = Path(".env")) -> None:
    """Load simple KEY=VALUE entries from .env without overriding the shell."""

    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_settings() -> Settings:
    """Load settings from environment variables."""

    _load_dotenv()
    sqlite_db_path = Path(_required_env("SQLITE_DB_PATH")).expanduser().resolve()
    return Settings(
        openai_api_key=_required_env("OPENAI_API_KEY"),
        sqlite_db_path=sqlite_db_path,
        api_key=_required_env("ASKDB_API_KEY"),
        openai_model=os.getenv("ASKDB_OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
        host=os.getenv("ASKDB_HOST", "127.0.0.1").strip() or "127.0.0.1",
        port=int(os.getenv("ASKDB_PORT", "8765")),
        pending_ttl_seconds=int(os.getenv("ASKDB_PENDING_TTL_SECONDS", "3600")),
        max_rows=int(os.getenv("ASKDB_MAX_ROWS", "100")),
    )
