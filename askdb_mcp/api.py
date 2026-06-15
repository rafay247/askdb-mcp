"""FastAPI approval API and local browser UI."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from askdb_mcp.config import Settings
from askdb_mcp.models import PendingStatus
from askdb_mcp.pending_store import PendingWriteStore
from askdb_mcp.service import AskDBService
from askdb_mcp.sqlite_executor import SQLiteExecutor


UI_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>askdb_mcp</title>
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
      width: min(1160px, calc(100% - 32px));
      margin: 28px auto 40px;
      display: grid;
      grid-template-columns: 86px minmax(0, 1fr);
      gap: 22px;
      animation: enter .45s ease-out both;
    }
    @keyframes enter {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .rail {
      min-height: calc(100vh - 68px);
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
    .shell { display: grid; gap: 18px; }
    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.25fr) minmax(260px, .75fr);
      gap: 18px;
      align-items: end;
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
      box-shadow: var(--shadow);
      transform: translateX(-10px);
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
      min-height: 118px;
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
      grid-template-columns: minmax(0, 1.08fr) minmax(300px, .92fr);
      gap: 18px;
      align-items: start;
    }
    .result-panel { min-height: 280px; }
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
    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; }
      .rail { min-height: auto; height: 58px; }
      .rail span { writing-mode: horizontal-tb; transform: none; }
      .hero, .workspace { grid-template-columns: 1fr; }
      .command { transform: none; box-shadow: 8px 8px 0 #17120d; }
    }
  </style>
</head>
<body>
  <main>
    <aside class="rail"><span>SQLite Ledger</span></aside>
    <div class="shell">
      <header class="hero">
        <div>
          <div class="badge">Local approval console</div>
          <h1>askdb_mcp</h1>
        </div>
        <div class="metrics">
          <div class="metric"><span>Database</span><strong id="dbState">checking</strong></div>
          <div class="metric"><span>Pending</span><strong id="pendingCount">0</strong></div>
        </div>
      </header>

      <section class="command">
        <label for="apiKey">Approval key</label>
        <input id="apiKey" type="password" placeholder="ASKDB_API_KEY" autocomplete="off" />
        <label for="question">Command</label>
        <textarea id="question" placeholder="add new customer&#10;Rafay rafayf2@gmail.com Multan"></textarea>
        <div class="row">
          <button id="askBtn">Run command</button>
          <button id="refreshBtn" class="secondary">Refresh pending</button>
          <span id="status" class="status">idle</span>
        </div>
      </section>

      <div class="workspace">
        <section class="result-panel">
          <h2>Result</h2>
          <div id="result" class="empty">No command has run yet.</div>
        </section>

        <section>
          <h2>Pending Writes</h2>
          <div id="pending" class="empty">No pending writes loaded.</div>
        </section>
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
    const savedKey = localStorage.getItem("askdb_api_key");
    if (savedKey) apiKey.value = savedKey;

    function headers() {
      return {"Content-Type": "application/json", "X-AskDB-Key": apiKey.value};
    }

    function setStatus(text) {
      statusEl.textContent = text;
    }

    function escapeHtml(value) {
      return value.replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}[ch]));
    }

    function renderRows(data) {
      if (!data.columns || !data.rows || data.rows.length === 0) return "<p>No rows returned.</p>";
      const head = data.columns.map(c => `<th>${escapeHtml(c)}</th>`).join("");
      const rows = data.rows.map(row => `<tr>${data.columns.map(c => `<td>${escapeHtml(String(row[c] ?? ""))}</td>`).join("")}</tr>`).join("");
      return `<table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>`;
    }

    async function askDatabase() {
      localStorage.setItem("askdb_api_key", apiKey.value);
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
        if (!response.ok || data.ok === false) throw new Error(data.detail || data.error || "Request failed");
        const sql = data.sql ? `<h3>SQL</h3><pre class="sql">${escapeHtml(data.sql)}</pre>` : "";
        const explanation = data.explanation ? `<p>${escapeHtml(data.explanation)}</p>` : "";
        const approval = data.pending_write_id ? `<p><strong>Pending write:</strong> ${escapeHtml(data.pending_write_id)}</p>` : "";
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
      localStorage.setItem("askdb_api_key", apiKey.value);
      try {
        const response = await fetch("/pending-writes", {headers: headers()});
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Could not load pending writes");
        pendingCount.textContent = data.count;
        if (!data.items.length) {
          pendingEl.className = "empty";
          pendingEl.textContent = "No pending writes.";
          return;
        }
        pendingEl.className = "";
        pendingEl.innerHTML = data.items.map(item => `
          <div class="pending-card">
            <p><strong>${escapeHtml(item.status)}</strong> ${escapeHtml(item.id)}</p>
            <pre class="sql">${escapeHtml(item.sql)}</pre>
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

    async function approveWrite(id) {
      const response = await fetch(`/pending-writes/${id}/approve`, {method: "POST", headers: headers()});
      resultEl.className = "";
      resultEl.innerHTML = `<pre>${escapeHtml(JSON.stringify(await response.json(), null, 2))}</pre>`;
      await loadPending();
    }

    async function rejectWrite(id) {
      const response = await fetch(`/pending-writes/${id}/reject`, {method: "POST", headers: headers()});
      resultEl.className = "";
      resultEl.innerHTML = `<pre>${escapeHtml(JSON.stringify(await response.json(), null, 2))}</pre>`;
      await loadPending();
    }

    async function loadHealth() {
      const response = await fetch("/health");
      const data = await response.json();
      dbState.textContent = data.ok ? "online" : "offline";
      pendingCount.textContent = data.pending_writes ?? 0;
    }

    document.querySelector("#askBtn").addEventListener("click", askDatabase);
    document.querySelector("#refreshBtn").addEventListener("click", loadPending);
    loadHealth();
    if (apiKey.value) loadPending();
  </script>
</body>
</html>
"""


class AskRequest(BaseModel):
    question: str


def create_app(
    settings: Settings,
    store: PendingWriteStore,
    executor: SQLiteExecutor,
    service: AskDBService | None = None,
) -> FastAPI:
    app = FastAPI(title="askdb_mcp approval API", version="0.1.0")

    def require_api_key(x_askdb_key: str | None = Header(default=None, alias="X-AskDB-Key")) -> None:
        if x_askdb_key != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing X-AskDB-Key header.",
            )

    @app.get("/", response_class=HTMLResponse)
    def ui() -> str:
        return UI_HTML

    @app.get("/health")
    def health() -> dict[str, object]:
        pending_items = [item for item in store.list() if item.status == PendingStatus.PENDING]
        return {
            "ok": True,
            "database": str(settings.sqlite_db_path),
            "pending_writes": len(pending_items),
        }

    @app.post("/ask", dependencies=[Depends(require_api_key)])
    def ask_database(request: AskRequest) -> dict[str, Any]:
        if service is None:
            raise HTTPException(status_code=503, detail="AskDB service is not available.")
        return service.ask_database(request.question)

    @app.get("/pending-writes", dependencies=[Depends(require_api_key)])
    def list_pending_writes() -> dict[str, object]:
        items = [
            pending.to_dict()
            for pending in store.list()
            if pending.status == PendingStatus.PENDING
        ]
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
