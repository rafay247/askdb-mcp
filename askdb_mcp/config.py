"""Runtime configuration for askdb_mcp."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PLACEHOLDER_API_KEYS = {"change-me-local-key", "change-me", "replace_me"}
HOSTED_DEMO_DB_PATH = Path("/tmp/askdb_demo.sqlite")


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    sqlite_db_path: Path
    api_key: str | None
    openai_model: str = "gpt-4o-mini"
    host: str = "127.0.0.1"
    port: int = 8765
    pending_ttl_seconds: int = 3600
    max_rows: int = 100
    seed_demo_db: bool = False
    hosted: bool = False
    # False = "optional" auth mode: requests without a key are allowed (testing only).
    require_api_key: bool = True


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable {name}.")
    return value


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


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


def is_hosted() -> bool:
    """True when running on a serverless host such as Vercel."""

    return bool(os.getenv("VERCEL")) or _env_flag("ASKDB_HOSTED", False)


def load_settings() -> Settings:
    """Load settings from environment variables."""

    _load_dotenv()
    hosted = is_hosted()

    db_env = os.getenv("SQLITE_DB_PATH", "").strip()
    if db_env:
        sqlite_db_path = Path(db_env).expanduser().resolve()
    elif hosted:
        # Serverless filesystems are read-only except /tmp.
        sqlite_db_path = HOSTED_DEMO_DB_PATH
    else:
        raise RuntimeError("Missing required environment variable SQLITE_DB_PATH.")

    auth_mode = os.getenv("ASKDB_AUTH_MODE", "required").strip().lower() or "required"
    if auth_mode not in {"required", "optional"}:
        raise RuntimeError("ASKDB_AUTH_MODE must be 'required' or 'optional'.")
    require_api_key = auth_mode == "required"

    api_key = _required_env("ASKDB_API_KEY") if require_api_key else os.getenv("ASKDB_API_KEY", "").strip() or None
    if hosted and api_key and (api_key.lower() in PLACEHOLDER_API_KEYS or len(api_key) < 12):
        raise RuntimeError(
            "ASKDB_API_KEY is a placeholder or shorter than 12 characters; "
            "set a strong key before exposing AskDB publicly."
        )

    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip() or None,
        sqlite_db_path=sqlite_db_path,
        api_key=api_key,
        openai_model=os.getenv("ASKDB_OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
        host=os.getenv("ASKDB_HOST", "127.0.0.1").strip() or "127.0.0.1",
        port=int(os.getenv("ASKDB_PORT", "8765")),
        pending_ttl_seconds=int(os.getenv("ASKDB_PENDING_TTL_SECONDS", "3600")),
        max_rows=int(os.getenv("ASKDB_MAX_ROWS", "100")),
        seed_demo_db=_env_flag("ASKDB_SEED_DEMO_DB", hosted and not db_env),
        hosted=hosted,
        require_api_key=require_api_key,
    )
