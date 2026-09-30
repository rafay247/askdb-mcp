import pytest

from askdb_mcp import config


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # avoid picking up a developer .env
    for name in ["VERCEL", "ASKDB_HOSTED", "SQLITE_DB_PATH", "ASKDB_API_KEY", "OPENAI_API_KEY", "ASKDB_SEED_DEMO_DB", "ASKDB_AUTH_MODE"]:
        monkeypatch.delenv(name, raising=False)


def test_local_requires_db_path(monkeypatch):
    monkeypatch.setenv("ASKDB_API_KEY", "local")
    with pytest.raises(RuntimeError, match="SQLITE_DB_PATH"):
        config.load_settings()


def test_hosted_defaults_to_seeded_tmp_db(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("ASKDB_API_KEY", "a-strong-demo-key")
    settings = config.load_settings()
    assert settings.sqlite_db_path == config.HOSTED_DEMO_DB_PATH
    assert settings.seed_demo_db is True
    assert settings.openai_api_key is None


def test_hosted_rejects_weak_api_key(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("ASKDB_API_KEY", "change-me-local-key")
    with pytest.raises(RuntimeError, match="ASKDB_API_KEY"):
        config.load_settings()


def test_optional_auth_mode_needs_no_key(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("ASKDB_AUTH_MODE", "optional")
    settings = config.load_settings()
    assert settings.require_api_key is False
    assert settings.api_key is None


def test_invalid_auth_mode(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("ASKDB_AUTH_MODE", "maybe")
    with pytest.raises(RuntimeError, match="ASKDB_AUTH_MODE"):
        config.load_settings()
