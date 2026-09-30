import json

import pytest
from fastapi.testclient import TestClient

from askdb_mcp.api import create_app
from askdb_mcp.config import Settings
from askdb_mcp.openai_sql_generator import OpenAISqlGenerator
from askdb_mcp.pending_store import PendingWriteStore
from askdb_mcp.schema_service import SchemaService
from askdb_mcp.service import AskDBService
from askdb_mcp.sqlite_executor import SQLiteExecutor
from askdb_mcp.web import create_hosted_app

KEY = "test-key-123456"
AUTH = {"X-AskDB-Key": KEY}


@pytest.fixture
def client(demo_db):
    # No OpenAI key: the built-in sample fallback answers demo questions.
    settings = Settings(openai_api_key=None, sqlite_db_path=demo_db, api_key=KEY)
    service = AskDBService(
        schema_service=SchemaService(demo_db),
        sql_generator=OpenAISqlGenerator(settings),
        executor=SQLiteExecutor(demo_db),
        pending_store=PendingWriteStore(60),
    )
    return TestClient(create_app(settings, service))


def test_ui_and_health_are_public(client):
    assert "AskDB" in client.get("/").text
    health = client.get("/health").json()
    assert health["database"] == "demo.sqlite"
    assert health["openai_configured"] is False


@pytest.mark.parametrize("path", ["/pending-writes", "/schema"])
def test_requires_key(client, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"X-AskDB-Key": "wrong"}).status_code == 401


def test_read_and_write_flow(client):
    read = client.post("/ask", headers=AUTH, json={"question": "show all customers"}).json()
    assert read["status"] == "executed" and read["row_count"] == 6

    write = client.post(
        "/ask", headers=AUTH, json={"question": "add customer Alex Demo alex.demo@example.com Paris"}
    ).json()
    assert write["status"] == "pending_approval"
    assert client.get("/pending-writes", headers=AUTH).json()["count"] == 1

    pending_id = write["pending_write_id"]
    approved = client.post(f"/pending-writes/{pending_id}/approve", headers=AUTH).json()
    assert approved["status"] == "executed"
    assert client.post(f"/pending-writes/{pending_id}/approve", headers=AUTH).status_code == 409
    assert client.post("/pending-writes/nope/reject", headers=AUTH).status_code == 404

    read = client.post("/ask", headers=AUTH, json={"question": "show all customers"}).json()
    assert read["row_count"] == 7


def test_unknown_question_without_openai(client):
    response = client.post("/ask", headers=AUTH, json={"question": "what is the meaning of life"}).json()
    assert response["ok"] is False
    assert "OPENAI_API_KEY" in response["detail"]


MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def _rpc(method, params, id_=1):
    return {"jsonrpc": "2.0", "id": id_, "method": method, "params": params}


def test_mcp_endpoint_requires_key(client):
    response = client.post("/mcp", headers=MCP_HEADERS, json=_rpc("tools/list", {}))
    assert response.status_code == 401


def test_mcp_endpoint_lists_and_calls_tools(client):
    headers = {**MCP_HEADERS, "Authorization": f"Bearer {KEY}"}
    init = client.post(
        "/mcp",
        headers=headers,
        json=_rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}),
    )
    assert init.status_code == 200, init.text

    tools = client.post("/mcp", headers=headers, json=_rpc("tools/list", {}, 2)).json()
    names = {tool["name"] for tool in tools["result"]["tools"]}
    assert {"askdb_ask_database", "askdb_describe_schema", "askdb_get_pending_write"} <= names

    call = client.post(
        "/mcp",
        headers=headers,
        json=_rpc("tools/call", {"name": "askdb_ask_database", "arguments": {"question": "show all products"}}, 3),
    ).json()
    payload = json.loads(call["result"]["content"][0]["text"])
    assert payload["status"] == "executed" and payload["row_count"] == 6


def test_hosted_app_seeds_demo_db(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("ASKDB_API_KEY", KEY)
    monkeypatch.setenv("SQLITE_DB_PATH", str(tmp_path / "hosted.sqlite"))
    monkeypatch.setenv("ASKDB_SEED_DEMO_DB", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(create_hosted_app())
    assert client.get("/health").json()["mode"] == "hosted-demo"
    assert client.post("/ask", headers=AUTH, json={"question": "show all orders"}).json()["row_count"] == 6


def test_hosted_app_reports_missing_config(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("ASKDB_API_KEY", raising=False)
    response = TestClient(create_hosted_app()).get("/health")
    assert response.status_code == 503
    assert "ASKDB_API_KEY" in response.json()["detail"]


@pytest.fixture
def open_client(demo_db):
    settings = Settings(openai_api_key=None, sqlite_db_path=demo_db, api_key=KEY, require_api_key=False)
    service = AskDBService(
        schema_service=SchemaService(demo_db),
        sql_generator=OpenAISqlGenerator(settings),
        executor=SQLiteExecutor(demo_db),
        pending_store=PendingWriteStore(60),
    )
    return TestClient(create_app(settings, service))


def test_optional_mode_allows_read_and_write_without_key(open_client):
    assert open_client.get("/health").json()["auth_mode"] == "optional"
    write = open_client.post(
        "/ask", json={"question": "add customer Alex Demo alex.demo@example.com Paris"}
    ).json()
    assert write["status"] == "pending_approval"
    approved = open_client.post(f"/pending-writes/{write['pending_write_id']}/approve").json()
    assert approved["status"] == "executed"
    assert open_client.post("/ask", json={"question": "show all customers"}).json()["row_count"] == 7
    tools = open_client.post("/mcp", headers=MCP_HEADERS, json=_rpc("tools/list", {}))
    assert tools.status_code == 200


def test_optional_mode_still_accepts_right_key_and_rejects_wrong_key(open_client):
    assert open_client.get("/schema", headers=AUTH).status_code == 200
    assert open_client.get("/schema", headers={"X-AskDB-Key": "wrong"}).status_code == 401


def test_required_mode_reports_auth_mode(client):
    assert client.get("/health").json()["auth_mode"] == "required"


def test_favicon(client):
    for path in ["/favicon.svg", "/favicon.ico"]:
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/svg+xml")


def test_ui_script_has_no_raw_newlines_in_string_literals(client):
    # A "\n" inside the Python UI string once rendered as a real line break and broke the page script.
    html = client.get("/").text
    assert '.join("\\n")' in html
    assert '.join("\n")' not in html
