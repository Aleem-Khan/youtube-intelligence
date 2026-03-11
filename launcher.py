"""
THE GIANT — Web Launcher
Serves the professional launcher UI on localhost:7843
Streams live terminal output from all tools to the browser.
"""

import http.server
import subprocess
import threading
import sqlite3
import json
import os
import sys
import webbrowser
import urllib.parse
from datetime import datetime
from config import DB_FILE

# ── Active process (only one at a time) ──────────────────────────
active_proc   = None
proc_lock     = threading.Lock()
output_buffer = []
output_lock   = threading.Lock()

def get_stats():
    try:
        conn = sqlite3.connect(DB_FILE)
        c    = conn.cursor()
        c.execute("SELECT COUNT(*) FROM channels")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM channels WHERE is_golden=1")
        golden = c.fetchone()[0]
        try:
            c.execute("SELECT COUNT(*) FROM channels WHERE review_status='pending'")
            pending = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM channels WHERE review_status='rejected'")
            rejected = c.fetchone()[0]
        except:
            pending = rejected = 0
        c.execute("SELECT COUNT(DISTINCT niche) FROM channels")
        niches = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM keywords WHERE searched=1")
        kw_done = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM keywords")
        kw_total = c.fetchone()[0]
        conn.close()
        return {
            "total": total, "golden": golden,
            "pending": pending, "rejected": rejected,
            "niches": niches, "kw_done": kw_done, "kw_total": kw_total
        }
    except:
        return {"total":0,"golden":0,"pending":0,"rejected":0,"niches":0,"kw_done":0,"kw_total":0}


def run_process(cmd, label):
    global active_proc
    with proc_lock:
        if active_proc and active_proc.poll() is None:
            return False  # already running

    with output_lock:
        output_buffer.clear()
        output_buffer.append(f"[GIANT] Starting: {label}\n")

    def stream():
        global active_proc
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, cwd=os.getcwd(),
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )
        active_proc = proc
        for line in proc.stdout:
            with output_lock:
                output_buffer.append(line)
                if len(output_buffer) > 2000:
                    output_buffer.pop(0)
        proc.wait()
        with output_lock:
            output_buffer.append(f"\n[GIANT] Process finished. Exit code: {proc.returncode}\n")
        active_proc = None

    threading.Thread(target=stream, daemon=True).start()
    return True


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/launcher":
            self._html(LAUNCHER_HTML)

        elif path == "/api/stats":
            self._json(get_stats())

        elif path == "/api/output":
            since = int(params.get("since", ["0"])[0])
            with output_lock:
                lines = output_buffer[since:]
            self._json({"lines": lines, "total": len(output_buffer)})

        elif path == "/api/status":
            running = active_proc is not None and active_proc.poll() is None
            self._json({"running": running})

        elif path == "/api/run/discovery":
            ok = run_process([sys.executable, "giant.py"], "Full Auto Discovery")
            self._json({"ok": ok, "msg": "Discovery started" if ok else "Already running"})

        elif path == "/api/run/discovery-custom":
            niche = params.get("niche", [""])[0].strip()
            if not niche:
                self._json({"ok": False, "msg": "No niche provided"})
                return
            ok = run_process([sys.executable, "giant.py", "--custom", niche], f"Custom: {niche}")
            self._json({"ok": ok, "msg": f"Started for: {niche}" if ok else "Already running"})

        elif path == "/api/run/review":
            import subprocess as sp
            sp.Popen([sys.executable, "review.py"], cwd=os.getcwd())
            self._json({"ok": True, "msg": "Review dashboard opening..."})

        elif path == "/api/run/reset":
            ok = run_process([sys.executable, "reset_db.py"], "Database Reset")
            self._json({"ok": ok})

        elif path == "/api/stop":
            with proc_lock:
                if active_proc and active_proc.poll() is None:
                    active_proc.terminate()
                    self._json({"ok": True, "msg": "Process stopped"})
                else:
                    self._json({"ok": False, "msg": "Nothing running"})

        else:
            self.send_response(404)
            self.end_headers()

    def _json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


LAUNCHER_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>THE GIANT — Command Center</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --bg:       #06060a;
  --bg2:      #0c0c14;
  --bg3:      #111120;
  --border:   #1c1c30;
  --accent:   #7b5ea7;
  --gold:     #d4a843;
  --green:    #3ecf8e;
  --red:      #e05c5c;
  --dim:      #3a3a5c;
  --text:     #c8c8e0;
  --muted:    #5a5a7a;
  --mono:     'Space Mono', monospace;
  --sans:     'Syne', sans-serif;
}

* { margin:0; padding:0; box-sizing:border-box; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  min-height: 100vh;
  overflow-x: hidden;
}

/* ── GRID BACKGROUND ── */
body::before {
  content:'';
  position:fixed; inset:0;
  background-image:
    linear-gradient(var(--border) 1px, transparent 1px),
    linear-gradient(90deg, var(--border) 1px, transparent 1px);
  background-size: 40px 40px;
  opacity: 0.4;
  pointer-events:none;
  z-index:0;
}

/* ── HEADER ── */
.header {
  position: relative; z-index:1;
  padding: 32px 48px 24px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  background: linear-gradient(180deg, #0a0a12 0%, transparent 100%);
}

.logo {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.logo-eyebrow {
  font-family: var(--mono);
  font-size: 0.65rem;
  color: var(--accent);
  letter-spacing: 4px;
  text-transform: uppercase;
}

.logo-title {
  font-family: var(--sans);
  font-size: 2.4rem;
  font-weight: 800;
  color: #fff;
  letter-spacing: -1px;
  line-height: 1;
}

.logo-sub {
  font-family: var(--mono);
  font-size: 0.7rem;
  color: var(--muted);
  letter-spacing: 2px;
  margin-top: 4px;
}

.status-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg3);
  border: 1px solid var(--border);
  padding: 8px 16px;
  border-radius: 100px;
  font-family: var(--mono);
  font-size: 0.72rem;
}

.status-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 8px var(--green);
  animation: pulse 2s infinite;
}

.status-dot.busy {
  background: var(--gold);
  box-shadow: 0 0 8px var(--gold);
}

@keyframes pulse {
  0%,100% { opacity:1; }
  50% { opacity:0.4; }
}

/* ── STAT BAR ── */
.stat-bar {
  position: relative; z-index:1;
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  border-bottom: 1px solid var(--border);
}

.stat-cell {
  padding: 20px 24px;
  border-right: 1px solid var(--border);
  position: relative;
}

.stat-cell:last-child { border-right: none; }

.stat-cell-label {
  font-family: var(--mono);
  font-size: 0.6rem;
  color: var(--muted);
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.stat-cell-value {
  font-family: var(--sans);
  font-size: 1.8rem;
  font-weight: 800;
  color: #fff;
  line-height: 1;
}

.stat-cell-value.gold  { color: var(--gold); }
.stat-cell-value.green { color: var(--green); }
.stat-cell-value.red   { color: var(--red); }
.stat-cell-value.accent { color: #a78bfa; }

/* ── MAIN LAYOUT ── */
.layout {
  position: relative; z-index:1;
  display: grid;
  grid-template-columns: 380px 1fr;
  min-height: calc(100vh - 200px);
}

/* ── LEFT PANEL ── */
.panel-left {
  border-right: 1px solid var(--border);
  padding: 32px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.section-label {
  font-family: var(--mono);
  font-size: 0.6rem;
  color: var(--accent);
  letter-spacing: 3px;
  text-transform: uppercase;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-label::after {
  content:'';
  flex:1;
  height:1px;
  background: var(--border);
}

/* ── PHASE BLOCKS ── */
.phase-block {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}

.phase-header {
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 12px;
}

.phase-num {
  font-family: var(--mono);
  font-size: 0.65rem;
  color: var(--muted);
  background: var(--bg3);
  border: 1px solid var(--border);
  padding: 2px 8px;
  border-radius: 4px;
}

.phase-name {
  font-size: 0.85rem;
  font-weight: 700;
  color: #fff;
  flex:1;
}

.phase-tag {
  font-family: var(--mono);
  font-size: 0.6rem;
  padding: 2px 8px;
  border-radius: 4px;
}

.phase-tag.active  { background: #3ecf8e22; color: var(--green); border:1px solid #3ecf8e44; }
.phase-tag.soon    { background: #ffffff11; color: var(--muted);  border:1px solid #333; }

.phase-actions {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* ── BUTTONS ── */
.btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg3);
  color: var(--text);
  font-family: var(--sans);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
  width: 100%;
}

.btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: #fff;
  background: #7b5ea711;
}

.btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.btn-icon {
  font-size: 1rem;
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.btn-text { flex:1; }
.btn-hint {
  font-family: var(--mono);
  font-size: 0.6rem;
  color: var(--muted);
}

.btn.primary {
  background: linear-gradient(135deg, #7b5ea722, #4c1d9522);
  border-color: var(--accent);
  color: #c4b5fd;
}

.btn.primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #7b5ea733, #4c1d9533);
  color: #fff;
}

.btn.gold-btn {
  background: #d4a84311;
  border-color: #d4a84344;
  color: var(--gold);
}

.btn.gold-btn:hover:not(:disabled) {
  background: #d4a84322;
  border-color: var(--gold);
}

.btn.danger {
  background: #e05c5c11;
  border-color: #e05c5c33;
  color: var(--red);
}

.btn.danger:hover:not(:disabled) {
  background: #e05c5c22;
  border-color: var(--red);
}

.btn.stop-btn {
  background: #e05c5c22;
  border-color: var(--red);
  color: var(--red);
}

/* ── CUSTOM NICHE INPUT ── */
.custom-row {
  display: flex;
  gap: 6px;
}

.custom-input {
  flex:1;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: #fff;
  font-family: var(--sans);
  font-size: 0.8rem;
  padding: 10px 14px;
  outline: none;
  transition: border-color 0.15s;
}

.custom-input:focus {
  border-color: var(--accent);
}

.custom-input::placeholder { color: var(--muted); }

.custom-btn {
  background: var(--accent);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-family: var(--sans);
  font-size: 0.8rem;
  font-weight: 700;
  padding: 10px 16px;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.custom-btn:hover { background: #9b7ec7; }

/* ── RIGHT PANEL: TERMINAL ── */
.panel-right {
  display: flex;
  flex-direction: column;
}

.terminal-header {
  padding: 20px 28px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 16px;
  background: var(--bg2);
}

.terminal-dots {
  display: flex;
  gap: 6px;
}

.dot {
  width: 10px; height: 10px;
  border-radius: 50%;
}

.dot-red   { background: #e05c5c; }
.dot-gold  { background: #d4a843; }
.dot-green { background: #3ecf8e; }

.terminal-title {
  font-family: var(--mono);
  font-size: 0.72rem;
  color: var(--muted);
  letter-spacing: 1px;
}

.terminal-body {
  flex:1;
  background: #04040a;
  padding: 20px 24px;
  overflow-y: auto;
  max-height: calc(100vh - 320px);
  font-family: var(--mono);
  font-size: 0.75rem;
  line-height: 1.7;
  color: #7878a8;
}

.terminal-body .line-gold    { color: var(--gold); }
.terminal-body .line-green   { color: var(--green); }
.terminal-body .line-red     { color: var(--red); }
.terminal-body .line-accent  { color: #a78bfa; }
.terminal-body .line-white   { color: #e0e0e0; }
.terminal-body .line-dim     { color: #3a3a5a; }

.terminal-footer {
  padding: 12px 24px;
  border-top: 1px solid var(--border);
  background: var(--bg2);
  font-family: var(--mono);
  font-size: 0.65rem;
  color: var(--muted);
  display: flex;
  justify-content: space-between;
}

/* ── TOAST ── */
.toast {
  position: fixed;
  bottom: 28px; right: 28px;
  background: var(--bg3);
  border: 1px solid var(--accent);
  color: #c4b5fd;
  padding: 12px 20px;
  border-radius: 8px;
  font-family: var(--mono);
  font-size: 0.78rem;
  opacity: 0;
  transform: translateY(8px);
  transition: all 0.25s;
  z-index: 9999;
  pointer-events: none;
}

.toast.show { opacity:1; transform:translateY(0); }

/* ── RESPONSIVE ── */
@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  .stat-bar { grid-template-columns: repeat(3,1fr); }
  .panel-right { min-height: 400px; }
}
</style>
</head>
<body>

<div class="header">
  <div class="logo">
    <div class="logo-eyebrow">Intelligence System v2</div>
    <div class="logo-title">THE GIANT</div>
    <div class="logo-sub">YouTube Channel Discovery · Multi-Niche · Manual Review</div>
  </div>
  <div class="status-pill">
    <div class="status-dot" id="status-dot"></div>
    <span id="status-text">IDLE</span>
  </div>
</div>

<div class="stat-bar">
  <div class="stat-cell">
    <div class="stat-cell-label">Total Found</div>
    <div class="stat-cell-value" id="s-total">—</div>
  </div>
  <div class="stat-cell">
    <div class="stat-cell-label">Golden</div>
    <div class="stat-cell-value gold" id="s-golden">—</div>
  </div>
  <div class="stat-cell">
    <div class="stat-cell-label">Pending Review</div>
    <div class="stat-cell-value accent" id="s-pending">—</div>
  </div>
  <div class="stat-cell">
    <div class="stat-cell-label">Rejected</div>
    <div class="stat-cell-value red" id="s-rejected">—</div>
  </div>
  <div class="stat-cell">
    <div class="stat-cell-label">Niches</div>
    <div class="stat-cell-value" id="s-niches">—</div>
  </div>
  <div class="stat-cell">
    <div class="stat-cell-label">Keywords Done</div>
    <div class="stat-cell-value green" id="s-kw">—</div>
  </div>
</div>

<div class="layout">

  <!-- ── LEFT PANEL ── -->
  <div class="panel-left">

    <!-- PHASE 1 -->
    <div>
      <div class="section-label">Operations</div>

      <div class="phase-block">
        <div class="phase-header">
          <span class="phase-num">PHASE 01</span>
          <span class="phase-name">Discovery & Review</span>
          <span class="phase-tag active">ACTIVE</span>
        </div>
        <div class="phase-actions">
          <button class="btn primary" onclick="runDiscovery()" id="btn-discovery">
            <span class="btn-icon">⚡</span>
            <span class="btn-text">Auto Discovery — All Niches</span>
            <span class="btn-hint">20 niches</span>
          </button>

          <div class="custom-row">
            <input class="custom-input" id="custom-niche" placeholder="Custom niche name..." maxlength="60">
            <button class="custom-btn" onclick="runCustom()">Run</button>
          </div>

          <button class="btn gold-btn" onclick="openReview()" id="btn-review">
            <span class="btn-icon">★</span>
            <span class="btn-text">Open Manual Review</span>
            <span class="btn-hint">port 7842</span>
          </button>

          <button class="btn stop-btn" onclick="stopProcess()" id="btn-stop" style="display:none">
            <span class="btn-icon">■</span>
            <span class="btn-text">Stop Current Process</span>
          </button>
        </div>
      </div>
    </div>

    <!-- PHASE 2 & 3 -->
    <div>
      <div class="phase-block">
        <div class="phase-header">
          <span class="phase-num">PHASE 02</span>
          <span class="phase-name">Video Data Scraper</span>
          <span class="phase-tag soon">COMING SOON</span>
        </div>
        <div class="phase-actions">
          <button class="btn" disabled>
            <span class="btn-icon">📹</span>
            <span class="btn-text">Scrape Video Data</span>
            <span class="btn-hint">not built yet</span>
          </button>
        </div>
      </div>
    </div>

    <div>
      <div class="phase-block">
        <div class="phase-header">
          <span class="phase-num">PHASE 03</span>
          <span class="phase-name">Pattern Engine</span>
          <span class="phase-tag soon">COMING SOON</span>
        </div>
        <div class="phase-actions">
          <button class="btn" disabled>
            <span class="btn-icon">🧠</span>
            <span class="btn-text">Extract Patterns</span>
            <span class="btn-hint">not built yet</span>
          </button>
        </div>
      </div>
    </div>

    <!-- TOOLS -->
    <div>
      <div class="section-label">Tools</div>
      <div style="display:flex;flex-direction:column;gap:8px;">
        <button class="btn" onclick="refreshStats()">
          <span class="btn-icon">↻</span>
          <span class="btn-text">Refresh Stats</span>
        </button>
        <button class="btn danger" onclick="resetDB()">
          <span class="btn-icon">⚠</span>
          <span class="btn-text">Reset Database</span>
          <span class="btn-hint">wipes all data</span>
        </button>
      </div>
    </div>

  </div>

  <!-- ── RIGHT PANEL: TERMINAL ── -->
  <div class="panel-right">
    <div class="terminal-header">
      <div class="terminal-dots">
        <div class="dot dot-red"></div>
        <div class="dot dot-gold"></div>
        <div class="dot dot-green"></div>
      </div>
      <div class="terminal-title">LIVE OUTPUT — THE GIANT TERMINAL</div>
    </div>
    <div class="terminal-body" id="terminal">
      <span class="line-dim">══════════════════════════════════════════════════════</span><br>
      <span class="line-accent">  THE GIANT — Command Center</span><br>
      <span class="line-dim">──────────────────────────────────────────────────────</span><br>
      <span class="line-dim">  Select an operation from the left panel to begin.</span><br>
      <span class="line-dim">  Output from all processes will stream here live.</span><br>
      <span class="line-dim">══════════════════════════════════════════════════════</span><br>
    </div>
    <div class="terminal-footer">
      <span id="footer-status">READY</span>
      <span id="footer-time"></span>
    </div>
  </div>

</div>

<div class="toast" id="toast"></div>

<script>
let outputIndex = 0;
let polling     = false;
let isRunning   = false;

// ── Stats ──────────────────────────────────────────────────────
async function refreshStats() {
  try {
    const r = await fetch('/api/stats');
    const s = await r.json();
    document.getElementById('s-total').textContent   = s.total;
    document.getElementById('s-golden').textContent  = s.golden;
    document.getElementById('s-pending').textContent = s.pending;
    document.getElementById('s-rejected').textContent= s.rejected;
    document.getElementById('s-niches').textContent  = s.niches;
    document.getElementById('s-kw').textContent      = s.kw_done + '/' + s.kw_total;
  } catch(e) {}
}

// ── Terminal output polling ─────────────────────────────────────
async function pollOutput() {
  if (!polling) return;
  try {
    const r    = await fetch('/api/output?since=' + outputIndex);
    const data = await r.json();
    if (data.lines.length > 0) {
      const term = document.getElementById('terminal');
      data.lines.forEach(line => {
        const span = document.createElement('span');
        const cls  = classifyLine(line);
        if (cls) span.className = cls;
        span.textContent = line;
        term.appendChild(span);
      });
      term.scrollTop = term.scrollHeight;
      outputIndex = data.total;
      refreshStats();
    }
  } catch(e) {}
  setTimeout(pollOutput, 400);
}

function classifyLine(line) {
  if (line.includes('★ GOLDEN') || line.includes('GOLDEN'))       return 'line-gold';
  if (line.includes('COMPLETE') || line.includes('finished'))      return 'line-green';
  if (line.includes('Error') || line.includes('ERROR'))            return 'line-red';
  if (line.includes('[GIANT]') || line.includes('==='))            return 'line-accent';
  if (line.includes('Promising') || line.includes('Score:'))       return 'line-white';
  if (line.trim() === '' || line.startsWith('  ─'))                return 'line-dim';
  return '';
}

// ── Status check ───────────────────────────────────────────────
async function checkStatus() {
  try {
    const r    = await fetch('/api/status');
    const data = await r.json();
    setRunning(data.running);
  } catch(e) {}
  setTimeout(checkStatus, 2000);
}

function setRunning(running) {
  isRunning = running;
  const dot  = document.getElementById('status-dot');
  const txt  = document.getElementById('status-text');
  const stop = document.getElementById('btn-stop');
  const disc = document.getElementById('btn-discovery');
  const rev  = document.getElementById('btn-review');

  if (running) {
    dot.className  = 'status-dot busy';
    txt.textContent = 'RUNNING';
    stop.style.display = '';
    disc.disabled  = true;
    document.getElementById('footer-status').textContent = 'RUNNING...';
  } else {
    dot.className  = 'status-dot';
    txt.textContent = 'IDLE';
    stop.style.display = 'none';
    disc.disabled  = false;
    document.getElementById('footer-status').textContent = 'READY';
  }
}

// ── Actions ────────────────────────────────────────────────────
async function runDiscovery() {
  if (isRunning) { toast('Already running'); return; }
  clearTerminal();
  polling = true; pollOutput();
  const r    = await fetch('/api/run/discovery');
  const data = await r.json();
  toast(data.msg);
}

async function runCustom() {
  const niche = document.getElementById('custom-niche').value.trim();
  if (!niche) { toast('Enter a niche name first'); return; }
  if (isRunning) { toast('Already running'); return; }
  clearTerminal();
  polling = true; pollOutput();
  const r    = await fetch('/api/run/discovery-custom?niche=' + encodeURIComponent(niche));
  const data = await r.json();
  toast(data.msg);
  document.getElementById('custom-niche').value = '';
}

async function openReview() {
  const r    = await fetch('/api/run/review');
  const data = await r.json();
  toast('Review dashboard opening...');
}

async function stopProcess() {
  const r    = await fetch('/api/stop');
  const data = await r.json();
  toast(data.msg);
}

async function resetDB() {
  if (!confirm('Reset database? This deletes ALL channel data.')) return;
  if (isRunning) { toast('Stop process first'); return; }
  clearTerminal();
  polling = true; pollOutput();
  const r    = await fetch('/api/run/reset');
  const data = await r.json();
  toast('Database reset started');
}

function clearTerminal() {
  document.getElementById('terminal').innerHTML = '';
  outputIndex = 0;
}

// ── Toast ──────────────────────────────────────────────────────
function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2800);
}

// ── Clock ──────────────────────────────────────────────────────
function clock() {
  const now = new Date();
  document.getElementById('footer-time').textContent =
    now.toLocaleTimeString('en-GB', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
}
setInterval(clock, 1000); clock();

// ── Boot ───────────────────────────────────────────────────────
refreshStats();
checkStatus();
</script>
</body>
</html>'''


if __name__ == "__main__":
    port = 7843
    server = http.server.HTTPServer(("localhost", port), Handler)

    print("\n" + "="*55)
    print("  THE GIANT — Command Center")
    print("="*55)
    print(f"  Launcher URL : http://localhost:{port}")
    print(f"  Press Ctrl+C to shut down")
    print("="*55 + "\n")

    webbrowser.open(f"http://localhost:{port}")
    server.serve_forever()
