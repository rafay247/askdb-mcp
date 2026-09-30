"""FastAPI approval API and local browser UI."""

from __future__ import annotations

import hmac
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from pydantic import BaseModel, Field
from starlette.datastructures import Headers
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from askdb_mcp.config import Settings
from askdb_mcp.mcp_tools import build_mcp
from askdb_mcp.service import AskDBService


UI_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AskDB</title>
  <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  <style>
    @import url("https://fonts.googleapis.com/css2?family=Fraunces:wght@700;800&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap");
    :root {
      --paper: #f4efe4;
      --panel: #fffaf0;
      --ink: #17120d;
      --muted: #6b6254;
      --line: #22180f;
      --accent: #19c37d;
      --danger: #b3261e;
      --code: #111827;
      --code-soft: #202a3b;
      --shadow: 12px 12px 0 #17120d;
      --radius: 8px;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: "IBM Plex Sans", "Trebuchet MS", sans-serif;
      background:
        linear-gradient(90deg, rgba(23,18,13,.05) 1px, transparent 1px) 0 0 / 44px 44px,
        linear-gradient(rgba(23,18,13,.04) 1px, transparent 1px) 0 0 / 44px 44px,
        var(--paper);
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image: radial-gradient(rgba(23,18,13,.14) .7px, transparent .7px);
      background-size: 9px 9px;
      opacity: .26;
    }
    main {
      width: min(1480px, calc(100% - 36px));
      margin: 22px auto 36px;
      display: grid;
      grid-template-columns: 64px minmax(0, 1fr);
      gap: 18px;
      animation: enter .45s ease-out both;
    }
    @keyframes enter {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .rail {
      min-height: calc(100vh - 58px);
      border: 2px solid var(--line);
      background: var(--ink);
      color: var(--paper);
      border-radius: var(--radius);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 8px 8px 0 rgba(23,18,13,.22);
    }
    .rail span {
      writing-mode: vertical-rl;
      transform: rotate(180deg);
      letter-spacing: .16em;
      font-weight: 700;
      text-transform: uppercase;
    }
    .shell { display: grid; gap: 16px; }
    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(300px, 390px);
      gap: 16px;
      align-items: center;
    }
    h1, h2, h3 { font-family: "Fraunces", Georgia, serif; margin: 0; letter-spacing: 0; }
    h1 { font-size: clamp(44px, 8vw, 92px); line-height: .88; max-width: 720px; }
    h2 { font-size: 25px; }
    h3 { font-size: 17px; margin: 14px 0 8px; }
    p { margin: 8px 0 0; color: var(--muted); }
    .badge {
      border: 2px solid var(--line);
      border-radius: 999px;
      padding: 8px 12px;
      width: fit-content;
      background: var(--accent);
      font-weight: 800;
      text-transform: uppercase;
      font-size: 12px;
    }
    section, .metric {
      background: var(--panel);
      border: 2px solid var(--line);
      border-radius: var(--radius);
      padding: 18px;
    }
    .command {
      box-shadow: 8px 8px 0 #17120d;
    }
    .command-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 320px;
      gap: 16px;
      align-items: start;
    }
    .key-field {
      min-width: 0;
    }
    .key-field label,
    .question-field label {
      margin-top: 0;
    }
    .key-field input {
      min-height: 44px;
    }
    .metrics {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .metric strong { display: block; font-size: 22px; }
    label {
      display: block;
      margin: 14px 0 7px;
      font-weight: 800;
      text-transform: uppercase;
      font-size: 12px;
      letter-spacing: .08em;
    }
    input, textarea {
      width: 100%;
      border: 2px solid var(--line);
      border-radius: var(--radius);
      padding: 12px;
      color: var(--ink);
      background: #fffdf8;
      font: inherit;
      outline: none;
    }
    textarea {
      min-height: 108px;
      resize: vertical;
      font-size: 18px;
      line-height: 1.45;
    }
    input:focus, textarea:focus, button:focus-visible {
      box-shadow: 0 0 0 4px rgba(25,195,125,.28);
    }
    button {
      min-height: 44px;
      border: 2px solid var(--line);
      border-radius: var(--radius);
      background: var(--accent);
      color: var(--ink);
      font: inherit;
      font-weight: 800;
      padding: 10px 15px;
      cursor: pointer;
      transition: transform .16s ease, box-shadow .16s ease, background .16s ease;
    }
    button:hover { transform: translate(-2px, -2px); box-shadow: 4px 4px 0 var(--line); }
    button.secondary { background: #fffdf8; }
    button.danger { background: #ffd8d4; color: var(--danger); }
    button:disabled { opacity: .55; cursor: not-allowed; transform: none; box-shadow: none; }
    .row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; align-items: center; }
    .status {
      min-height: 34px;
      display: inline-flex;
      align-items: center;
      border: 2px solid var(--line);
      border-radius: 999px;
      background: var(--ink);
      color: var(--paper);
      padding: 6px 12px;
      font-size: 13px;
      font-weight: 800;
      text-transform: uppercase;
    }
    .workspace {
      display: grid;
      grid-template-columns: minmax(0, 2.8fr) minmax(280px, .75fr);
      gap: 18px;
      align-items: start;
    }
    .result-panel { min-height: 560px; }
    .result-panel #result {
      min-height: 458px;
      overflow: auto;
    }
    .pending-panel {
      max-height: calc(100vh - 36px);
      overflow: auto;
    }
    .empty {
      color: var(--muted);
      border: 2px dashed rgba(23,18,13,.35);
      border-radius: var(--radius);
      padding: 20px;
    }
    pre {
      white-space: pre-wrap;
      background: var(--code);
      color: #f8fafc;
      border-radius: var(--radius);
      padding: 14px;
      overflow-x: auto;
      border: 2px solid var(--line);
    }
    .sql { background: var(--code-soft); color: #d7fff0; font-size: 14px; }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      background: #fffdf8;
      border: 2px solid var(--line);
      border-radius: var(--radius);
      overflow: hidden;
    }
    th, td {
      border-bottom: 1px solid rgba(23,18,13,.18);
      padding: 10px;
      text-align: left;
      vertical-align: top;
    }
    th { background: var(--ink); color: var(--paper); }
    tr:last-child td { border-bottom: 0; }
    .pending-card {
      border: 2px solid var(--line);
      border-radius: var(--radius);
      padding: 14px;
      margin-top: 12px;
      background: #fffdf8;
    }
    .pending-card strong { text-transform: uppercase; }
    .examples { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
    .chip {
      min-height: 32px;
      padding: 5px 11px;
      font-size: 13px;
      font-weight: 600;
      background: #fffdf8;
      border-radius: 999px;
    }
    .notice {
      margin-top: 12px;
      border: 2px dashed rgba(23,18,13,.45);
      border-radius: var(--radius);
      padding: 10px 12px;
      font-size: 14px;
      color: var(--muted);
    }
    .notice[hidden] { display: none; }
    .error-box { background: #ffd8d4; color: var(--danger); border-color: var(--danger); }
    .schema-table { margin-top: 12px; font-size: 14px; }
    .auth-toggle { display: flex; gap: 6px; margin-bottom: 10px; }
    .auth-toggle[hidden] { display: none; }
    .auth-toggle button { flex: 1; min-height: 36px; padding: 6px 10px; font-size: 13px; background: #fffdf8; }
    .auth-toggle button.active { background: var(--ink); color: var(--paper); }
    #apiKey:disabled { opacity: .5; }
    .schema-table code { font-size: 13px; color: var(--muted); }
    .side { display: grid; gap: 18px; position: sticky; top: 18px; align-self: start; }
    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; }
      .rail { min-height: auto; height: 58px; }
      .rail span { writing-mode: horizontal-tb; transform: none; }
      .hero, .command-grid, .workspace { grid-template-columns: 1fr; }
      .pending-panel { max-height: none; }
      .side { position: static; }
    }
  </style>
</head>
<body>
  <main>
    <aside class="rail"><span>SQLite Ledger</span></aside>
    <div class="shell">
      <header class="hero">
        <div>
          <div class="badge" id="modeBadge">Approval console</div>
          <h1>AskDB</h1>
          <p>Ask a SQLite database in plain English. Reads run instantly; writes wait for your approval.</p>
        </div>
        <div class="metrics">
          <div class="metric"><span>Connection</span><strong id="dbState">checking</strong></div>
          <div class="metric"><span>Pending</span><strong id="pendingCount">0</strong></div>
        </div>
      </header>

      <section class="command">
        <div class="command-grid">
          <div class="question-field">
            <label for="question">Command</label>
            <textarea id="question" placeholder="add new customer&#10;Alex Demo alex.demo@example.com Paris"></textarea>
            <div class="examples" id="examples">
              <button class="chip secondary" type="button">show all customers</button>
              <button class="chip secondary" type="button">customers in London</button>
              <button class="chip secondary" type="button">show all orders</button>
              <button class="chip secondary" type="button">show all products</button>
              <button class="chip secondary" type="button">add customer Alex Demo alex.demo@example.com Paris</button>
            </div>
          </div>
          <div class="key-field">
            <label for="apiKey">Access</label>
            <div class="auth-toggle" id="authToggle" hidden>
              <button type="button" id="withKeyBtn" class="active">With approval key</button>
              <button type="button" id="withoutKeyBtn">Without key</button>
            </div>
            <input id="apiKey" type="password" placeholder="ASKDB_API_KEY" autocomplete="off" />
            <p id="openaiNote"></p>
          </div>
        </div>
        <div class="row command-actions">
          <button id="askBtn">Run command</button>
          <button id="refreshBtn" class="secondary">Refresh pending</button>
          <span id="status" class="status">idle</span>
        </div>
        <div class="notice" id="hostedNotice" hidden>
          Hosted demo: the database is a sandbox copy that resets when the server restarts,
          and pending writes live in memory, so an old proposal may disappear.
        </div>
      </section>

      <div class="workspace">
        <section class="result-panel">
          <h2>Result</h2>
          <div id="result" class="empty">No command has run yet.</div>
        </section>

        <div class="side">
          <section class="pending-panel">
            <h2>Pending Writes</h2>
            <div id="pending" class="empty">No pending writes loaded.</div>
          </section>
          <section>
            <h2>Schema</h2>
            <div id="schema" class="empty">Enter the approval key to load tables.</div>
          </section>
        </div>
      </div>
    </div>
  </main>

  <script>
    const apiKey = document.querySelector("#apiKey");
    const question = document.querySelector("#question");
    const statusEl = document.querySelector("#status");
    const resultEl = document.querySelector("#result");
    const pendingEl = document.querySelector("#pending");
    const dbState = document.querySelector("#dbState");
    const pendingCount = document.querySelector("#pendingCount");
    const askBtn = document.querySelector("#askBtn");
    const schemaEl = document.querySelector("#schema");
    const storage = {
      get() { try { return localStorage.getItem("askdb_api_key"); } catch (e) { return null; } },
      set(v) { try { localStorage.setItem("askdb_api_key", v); } catch (e) {} },
      clear() { try { localStorage.removeItem("askdb_api_key"); } catch (e) {} },
    };
    const savedKey = storage.get();
    if (savedKey) apiKey.value = savedKey;

    // "Without key" is only offered when the server runs with ASKDB_AUTH_MODE=optional.
    let authOptional = false;
    let keyless = false;
    function hasAccess() { return keyless || Boolean(apiKey.value.trim()); }
    function setKeyless(value) {
      keyless = authOptional && value;
      try { localStorage.setItem("askdb_keyless", keyless ? "1" : "0"); } catch (e) {}
      apiKey.disabled = keyless;
      document.querySelector("#withKeyBtn").classList.toggle("active", !keyless);
      document.querySelector("#withoutKeyBtn").classList.toggle("active", keyless);
      setConnection(keyless ? "open" : (apiKey.value.trim() ? "key ready" : "locked"));
    }

    function headers() {
      const base = {"Content-Type": "application/json"};
      if (!keyless && apiKey.value.trim()) base["X-AskDB-Key"] = apiKey.value.trim();
      return base;
    }

    function setStatus(text) {
      statusEl.textContent = text;
    }

    function setConnection(text) {
      dbState.textContent = text;
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}[ch]));
    }

    function renderRows(data) {
      if (!data.columns || !data.rows || data.rows.length === 0) return "<p>No rows returned.</p>";
      const head = data.columns.map(c => `<th>${escapeHtml(c)}</th>`).join("");
      const rows = data.rows.map(row => `<tr>${data.columns.map(c => `<td>${escapeHtml(row[c])}</td>`).join("")}</tr>`).join("");
      const more = data.truncated ? `<p>Showing the first ${data.row_count} rows; more rows matched.</p>` : "";
      return `<table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>${more}`;
    }

    function renderError(message, data) {
      const sql = data && data.generated_sql ? `<h3>Generated SQL</h3><pre class="sql">${escapeHtml(data.generated_sql)}</pre>` : "";
      return `<pre class="error-box">${escapeHtml(message)}</pre>${sql}`;
    }

    function renderDecision(data, ok) {
      if (!ok) return renderError(data.detail || "Request failed", null);
      const lines = {
        executed: `Write executed. Rows affected: ${data.result ? data.result.affected_rows : 0}.`,
        failed: `Write failed and was not applied: ${data.error}`,
        rejected: "Write rejected. Nothing was changed.",
      };
      const text = lines[data.status] || `Status: ${data.status}`;
      const cls = data.status === "failed" ? "error-box" : "";
      return `<pre class="${cls}">${escapeHtml(text)}</pre><h3>SQL</h3><pre class="sql">${escapeHtml(data.sql)}</pre>`;
    }

    async function askDatabase() {
      if (!hasAccess()) {
        setConnection("locked");
        setStatus("locked");
        resultEl.className = "";
        resultEl.innerHTML = "<pre>Approval key required.</pre>";
        return;
      }
      if (!keyless) storage.set(apiKey.value);
      setStatus("working");
      askBtn.disabled = true;
      resultEl.className = "";
      resultEl.innerHTML = "";
      try {
        const response = await fetch("/ask", {
          method: "POST",
          headers: headers(),
          body: JSON.stringify({question: question.value})
        });
        const data = await response.json();
        if (response.status === 401) setConnection("invalid");
        if (!response.ok || data.ok === false) {
          const message = [data.error, typeof data.detail === "string" ? data.detail : null].filter(Boolean).join("\\n") || "Request failed";
          resultEl.innerHTML = renderError(message, data);
          setStatus("error");
          if (response.ok) await loadPending();
          return;
        }
        setConnection(keyless ? "open" : "connected");
        const sql = data.sql ? `<h3>SQL</h3><pre class="sql">${escapeHtml(data.sql)}</pre>` : "";
        const explanation = data.explanation ? `<p>${escapeHtml(data.explanation)}</p>` : "";
        const approval = data.pending_write_id ? `<p><strong>Waiting for approval.</strong> ${escapeHtml(data.risk_summary)} Approve or reject it in Pending Writes.</p>` : "";
        resultEl.innerHTML = `${explanation}${approval}${sql}${renderRows(data)}<pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
        setStatus(data.status || "done");
        await loadPending();
      } catch (error) {
        resultEl.innerHTML = `<pre>${escapeHtml(error.message)}</pre>`;
        setStatus("error");
      } finally {
        askBtn.disabled = false;
      }
    }

    async function loadPending() {
      if (!hasAccess()) {
        setConnection("locked");
        pendingCount.textContent = "0";
        pendingEl.className = "empty";
        pendingEl.textContent = "Enter approval key to load pending writes.";
        return;
      }
      try {
        const response = await fetch("/pending-writes", {headers: headers()});
        const data = await response.json();
        if (response.status === 401) setConnection("invalid");
        if (!response.ok) throw new Error(data.detail || "Could not load pending writes");
        setConnection(keyless ? "open" : "connected");
        pendingCount.textContent = data.count;
        if (!data.items.length) {
          pendingEl.className = "empty";
          pendingEl.textContent = "No pending writes.";
          return;
        }
        pendingEl.className = "";
        pendingEl.innerHTML = data.items.map(item => `
          <div class="pending-card">
            <p><strong>${escapeHtml(item.status)}</strong> ${escapeHtml(item.question)}</p>
            <pre class="sql">${escapeHtml(item.sql)}</pre>
            <p>${escapeHtml(item.risk_summary)}</p>
            <div class="row">
              <button onclick="approveWrite('${item.id}')">Approve</button>
              <button class="danger" onclick="rejectWrite('${item.id}')">Reject</button>
            </div>
          </div>
        `).join("");
      } catch (error) {
        pendingEl.className = "";
        pendingEl.innerHTML = `<pre>${escapeHtml(error.message)}</pre>`;
      }
    }

    async function decide(id, action) {
      setStatus("working");
      try {
        const response = await fetch(`/pending-writes/${id}/${action}`, {method: "POST", headers: headers()});
        const data = await response.json();
        resultEl.className = "";
        resultEl.innerHTML = renderDecision(data, response.ok);
        setStatus(response.ok ? data.status : "error");
      } catch (error) {
        resultEl.innerHTML = renderError(error.message, null);
        setStatus("error");
      }
      await loadPending();
    }

    function approveWrite(id) { return decide(id, "approve"); }
    function rejectWrite(id) { return decide(id, "reject"); }

    async function loadSchema() {
      if (!hasAccess()) return;
      try {
        const response = await fetch("/schema", {headers: headers()});
        if (!response.ok) return;
        const data = await response.json();
        schemaEl.className = "";
        schemaEl.innerHTML = data.tables.map(table => `
          <table class="schema-table"><thead><tr><th>${escapeHtml(table.name)}</th></tr></thead>
          <tbody>${table.columns.map(c => `<tr><td>${escapeHtml(c.name)} <code>${escapeHtml(c.type)}</code></td></tr>`).join("")}</tbody></table>
        `).join("");
      } catch (error) {}
    }

    async function loadHealth() {
      try {
        const response = await fetch("/health");
        const data = await response.json();
        if (!data.ok) {
          setConnection("offline");
          resultEl.className = "";
          resultEl.innerHTML = renderError([data.error, data.detail, data.hint].filter(Boolean).join("\\n"), null);
          return;
        }
        authOptional = data.auth_mode === "optional";
        document.querySelector("#authToggle").hidden = !authOptional;
        let savedKeyless = null;
        try { savedKeyless = localStorage.getItem("askdb_keyless"); } catch (e) {}
        // Default to the keyless option in optional mode unless the viewer picked the key before.
        setKeyless(authOptional && savedKeyless !== "0");
        pendingCount.textContent = data.pending_writes ?? 0;
        const hosted = data.mode === "hosted-demo";
        document.querySelector("#modeBadge").textContent = hosted ? "Hosted demo" : "Local approval console";
        document.querySelector("#hostedNotice").hidden = !hosted;
        document.querySelector("#openaiNote").textContent = data.openai_configured
          ? "OpenAI SQL generation is on."
          : "OpenAI is off: only the example prompts are understood.";
      } catch (error) {
        setConnection("offline");
      }
    }

    document.querySelector("#askBtn").addEventListener("click", askDatabase);
    document.querySelector("#refreshBtn").addEventListener("click", () => { loadPending(); loadSchema(); });
    question.addEventListener("keydown", event => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) askDatabase();
    });
    document.querySelectorAll("#examples .chip").forEach(chip => chip.addEventListener("click", () => {
      question.value = chip.textContent;
      question.focus();
    }));
    document.querySelector("#withKeyBtn").addEventListener("click", () => { setKeyless(false); loadPending(); loadSchema(); });
    document.querySelector("#withoutKeyBtn").addEventListener("click", () => { setKeyless(true); loadPending(); loadSchema(); });
    apiKey.addEventListener("input", () => {
      if (apiKey.value.trim()) {
        setConnection("key ready");
      } else {
        storage.clear();
        setConnection("locked");
      }
    });
    loadHealth().then(() => {
      if (hasAccess()) { loadPending(); loadSchema(); }
    });
  </script>
</body>
</html>
"""


FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="#17120d"/>
<path d="M16 18v28c0 4.4 7.2 8 16 8s16-3.6 16-8V18" fill="#19c37d" stroke="#f4efe4" stroke-width="3"/>
<path d="M16 32c0 4.4 7.2 8 16 8s16-3.6 16-8" fill="none" stroke="#f4efe4" stroke-width="3"/>
<ellipse cx="32" cy="18" rx="16" ry="8" fill="#19c37d" stroke="#f4efe4" stroke-width="3"/>
</svg>"""


class AskRequest(BaseModel):
    question: str = Field(max_length=2000)


def _key_matches(provided: str | None, expected: str | None) -> bool:
    return bool(provided and expected) and hmac.compare_digest(provided.encode(), expected.encode())


def is_authorized(settings: Settings, provided: str | None) -> bool:
    """A supplied key must be correct; no key is accepted only in optional auth mode."""

    provided = (provided or "").strip() or None
    if provided is None:
        return not settings.require_api_key
    if settings.api_key is None:
        # Optional mode with no key configured: there is nothing to check against.
        return True
    return _key_matches(provided, settings.api_key)


class McpHttpEndpoint:
    """Stateless streamable-HTTP MCP endpoint.

    A fresh session manager per request keeps it independent of ASGI lifespan
    events, which serverless hosts do not reliably deliver.
    """

    def __init__(self, service: AskDBService, settings: Settings) -> None:
        self.mcp_server = build_mcp(service)._mcp_server
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        headers = Headers(scope=scope)
        bearer = headers.get("authorization", "")
        token = bearer[7:].strip() if bearer.lower().startswith("bearer ") else None
        if not is_authorized(self.settings, headers.get("x-askdb-key") or token):
            response = JSONResponse(
                {"detail": "Invalid or missing X-AskDB-Key header or bearer token."},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
            await response(scope, receive, send)
            return
        manager = StreamableHTTPSessionManager(app=self.mcp_server, stateless=True, json_response=True)
        async with manager.run():
            await manager.handle_request(scope, receive, send)


def create_app(settings: Settings, service: AskDBService) -> FastAPI:
    app = FastAPI(title="AskDB approval API", version="0.2.0")

    def require_api_key(x_askdb_key: str | None = Header(default=None, alias="X-AskDB-Key")) -> None:
        if not is_authorized(settings, x_askdb_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing X-AskDB-Key header.",
            )

    @app.get("/", response_class=HTMLResponse)
    def ui() -> str:
        return UI_HTML

    @app.get("/favicon.svg", include_in_schema=False)
    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(FAVICON_SVG, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "ok": True,
            "database": settings.sqlite_db_path.name,
            "mode": "hosted-demo" if settings.hosted else "local",
            "openai_configured": settings.openai_api_key is not None,
            "auth_mode": "required" if settings.require_api_key else "optional",
            "pending_writes": len(service.list_pending()),
        }

    @app.post("/ask", dependencies=[Depends(require_api_key)])
    def ask_database(request: AskRequest) -> dict[str, Any]:
        return service.ask_database(request.question)

    @app.get("/schema", dependencies=[Depends(require_api_key)])
    def describe_schema() -> dict[str, Any]:
        return service.describe_schema()

    @app.get("/pending-writes", dependencies=[Depends(require_api_key)])
    def list_pending_writes() -> dict[str, object]:
        items = [pending.to_dict() for pending in service.list_pending()]
        return {"count": len(items), "items": items}

    @app.get("/pending-writes/{pending_id}", dependencies=[Depends(require_api_key)])
    def get_pending_write(pending_id: str) -> dict[str, object]:
        pending = service.get_pending(pending_id)
        if pending is None:
            raise HTTPException(status_code=404, detail="Pending write not found.")
        return pending.to_dict()

    @app.post("/pending-writes/{pending_id}/approve", dependencies=[Depends(require_api_key)])
    def approve_pending_write(pending_id: str) -> dict[str, object]:
        try:
            return service.approve_write(pending_id).to_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=_not_found_detail(settings)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/pending-writes/{pending_id}/reject", dependencies=[Depends(require_api_key)])
    def reject_pending_write(pending_id: str) -> dict[str, object]:
        try:
            return service.reject_write(pending_id).to_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=_not_found_detail(settings)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    app.router.routes.append(
        Route("/mcp", endpoint=McpHttpEndpoint(service, settings), methods=["GET", "POST", "DELETE"])
    )
    return app


def _not_found_detail(settings: Settings) -> str:
    if settings.hosted:
        # Serverless instances keep proposals in memory, so a cold start forgets them.
        return "Pending write not found. The hosted demo may have restarted; ask again to create a new proposal."
    return "Pending write not found."
