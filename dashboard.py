#!/usr/bin/env python3
"""
Coin Scanner Rig — Web Dashboard
Serves a live dashboard on the Pi that shows scan results on phone/tablet.
Run alongside coin_scanner_rig.py — it reads from the same results JSON.
"""

import json
import os
import glob
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

DASHBOARD_PORT = 8080
RESULTS_DIR = os.path.dirname(os.path.abspath(__file__))
REFRESH_MS = 2000  # auto-refresh every 2 seconds

DASHBOARD_HTML = """<!doctype html>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Coin Scanner Dashboard</title>
<style>
  :root {
    --bg: #0f172a;
    --card: #1e293b;
    --fg: #e5e7eb;
    --muted: #94a3b8;
    --green: #22c55e;
    --yellow: #eab308;
    --red: #ef4444;
    --blue: #3b82f6;
    --border: #334155;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--fg);
    font: 15px/1.5 ui-sans-serif, system-ui, -apple-system, sans-serif;
    min-height: 100vh;
  }
  .container { max-width: 900px; margin: 0 auto; padding: 16px; }

  /* Header */
  .header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 0; border-bottom: 1px solid var(--border); margin-bottom: 20px;
  }
  .header h1 { font-size: 22px; }
  .header .status {
    font-size: 13px; color: var(--muted);
    display: flex; align-items: center; gap: 8px;
  }
  .pulse {
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--green); animation: pulse 2s infinite;
  }
  .pulse.idle { background: var(--muted); animation: none; }
  @keyframes pulse {
    0%,100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  /* Summary cards */
  .summary {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px;
  }
  .card {
    background: var(--card); border-radius: 12px; padding: 16px;
    text-align: center; border: 1px solid var(--border);
  }
  .card .num { font-size: 32px; font-weight: 700; }
  .card .lbl { font-size: 12px; color: var(--muted); margin-top: 4px; }
  .card.green .num { color: var(--green); }
  .card.yellow .num { color: var(--yellow); }
  .card.red .num { color: var(--red); }
  .card.blue .num { color: var(--blue); }

  /* Results table */
  .results { background: var(--card); border-radius: 12px; overflow: hidden; border: 1px solid var(--border); }
  .results-header {
    display: grid; grid-template-columns: 60px 1fr 80px 80px 100px 100px;
    padding: 12px 16px; font-size: 12px; font-weight: 700; color: var(--muted);
    border-bottom: 1px solid var(--border); text-transform: uppercase;
  }
  .result-row {
    display: grid; grid-template-columns: 60px 1fr 80px 80px 100px 100px;
    padding: 12px 16px; border-bottom: 1px solid var(--border);
    align-items: center;
  }
  .result-row:last-child { border-bottom: none; }
  .result-row .slot { color: var(--muted); font-weight: 600; }
  .result-row .coin { font-weight: 600; }
  .result-row .coin .year { color: var(--muted); font-weight: 400; }
  .result-row .face { color: var(--muted); font-size: 13px; }
  .result-row .est { font-weight: 600; }
  .badge {
    display: inline-block; padding: 4px 10px; border-radius: 6px;
    font-size: 11px; font-weight: 700; text-transform: uppercase;
  }
  .badge.pass { background: rgba(34,197,94,0.2); color: var(--green); }
  .badge.review { background: rgba(234,179,8,0.2); color: var(--yellow); }
  .badge.rare { background: rgba(239,68,68,0.2); color: var(--red); }

  .varieties { font-size: 12px; color: var(--muted); margin-top: 4px; }
  .varieties span { color: var(--yellow); }

  .empty {
    text-align: center; padding: 60px 20px; color: var(--muted);
  }
  .empty .icon { font-size: 48px; margin-bottom: 12px; }

  @media (max-width: 600px) {
    .summary { grid-template-columns: repeat(2, 1fr); }
    .results-header, .result-row {
      grid-template-columns: 40px 1fr 70px 90px;
    }
    .col-face, .col-est { display: none; }
  }
</style>
<div class="container">
  <div class="header">
    <h1>🪙 Coin Scanner</h1>
    <div class="status">
      <span class="pulse" id="pulse"></span>
      <span id="status-text">Scanning...</span>
    </div>
  </div>

  <div class="summary">
    <div class="card blue">
      <div class="num" id="total">0</div>
      <div class="lbl">Total Scanned</div>
    </div>
    <div class="card green">
      <div class="num" id="passed">0</div>
      <div class="lbl">Passed</div>
    </div>
    <div class="card yellow">
      <div class="num" id="review">0</div>
      <div class="lbl">Check</div>
    </div>
    <div class="card red">
      <div class="num" id="rare">0</div>
      <div class="lbl">Rare</div>
    </div>
  </div>

  <div class="results">
    <div class="results-header">
      <div>Slot</div>
      <div>Coin</div>
      <div class="col-face">Face</div>
      <div class="col-est">Est. Value</div>
      <div>Status</div>
      <div>Action</div>
    </div>
    <div id="results-body">
      <div class="empty">
        <div class="icon">🪙</div>
        <div>Waiting for first coin...</div>
      </div>
    </div>
  </div>
</div>
<script>
  async function fetchResults() {
    try {
      const res = await fetch('/api/results');
      const data = await res.json();
      updateDashboard(data);
    } catch(e) {
      document.getElementById('status-text').textContent = 'Connection lost';
      document.getElementById('pulse').classList.add('idle');
    }
  }

  function updateDashboard(data) {
    const { total, passed, review, rare, results, scanning } = data;

    document.getElementById('total').textContent = total;
    document.getElementById('passed').textContent = passed;
    document.getElementById('review').textContent = review;
    document.getElementById('rare').textContent = rare;

    const pulse = document.getElementById('pulse');
    const statusText = document.getElementById('status-text');
    if (scanning) {
      pulse.classList.remove('idle');
      statusText.textContent = 'Scanning...';
    } else {
      pulse.classList.add('idle');
      statusText.textContent = 'Idle';
    }

    const body = document.getElementById('results-body');
    if (!results || results.length === 0) {
      body.innerHTML = '<div class="empty"><div class="icon">🪙</div><div>Waiting for first coin...</div></div>';
      return;
    }

    body.innerHTML = results.slice().reverse().map(r => {
      const d = r.result || {};
      const detections = d.detections || [];
      const disp = d.disposition || 'PASS';
      const badgeClass = disp.toLowerCase();
      const badgeText = disp === 'PASS' ? '🟢 Pass' : disp === 'REVIEW' ? '🟡 Check' : '🔴 Rare';
      const action = disp === 'PASS' ? '—' : '🆙 Pushed';

      let coinInfo = '<span class="coin">Unknown</span>';
      let faceVal = '—';
      let estVal = '—';
      let varieties = '';

      if (detections.length > 0) {
        const det = detections[0];
        const type = (det.type || 'unknown').replace('_', ' ');
        const year = det.year || '?';
        const mint = det.mint_mark ? ' ' + det.mint_mark : '';
        coinInfo = `<span class="coin">${type} <span class="year">${year}${mint}</span></span>`;
        faceVal = '$' + (det.face_value || 0).toFixed(2);
        estVal = '$' + (det.estimated_value || det.face_value || 0).toFixed(2);

        if (det.varieties_to_check) {
          varieties = '<div class="varieties">🔍 <span>' +
            det.varieties_to_check.map(v => v.description).join(', ') +
            '</span></div>';
        }

        if (det.rare && det.rare.is_rare) {
          varieties += `<div class="varieties">💰 ${det.rare.notes || ''}</div>`;
        }
      }

      return `<div class="result-row">
        <div class="slot">#${r.slot}</div>
        <div>${coinInfo}${varieties}</div>
        <div class="col-face face">${faceVal}</div>
        <div class="col-est est">${estVal}</div>
        <div><span class="badge ${badgeClass}">${badgeText}</span></div>
        <div>${action}</div>
      </div>`;
    }).join('');
  }

  fetchResults();
  setInterval(fetchResults, """ + str(REFRESH_MS) + """);
</script>
"""

# Shared state between scanner and dashboard
_latest_results = []
_scanning_active = False
_state_lock = threading.Lock()

def update_results(results_list, scanning=False):
    """Called by the scanner script to update the dashboard state."""
    global _latest_results, _scanning_active
    with _state_lock:
        _latest_results = results_list
        _scanning_active = scanning

def _load_from_json():
    """Load results from the latest JSON file."""
    global _latest_results
    files = sorted(glob.glob(os.path.join(RESULTS_DIR, "scan_results_*.json")))
    if files:
        try:
            with open(files[-1], "r") as f:
                _latest_results = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/results":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            with _state_lock:
                data = {
                    "total": len(_latest_results),
                    "passed": sum(1 for r in _latest_results if r.get("result", {}).get("disposition") == "PASS"),
                    "review": sum(1 for r in _latest_results if r.get("result", {}).get("disposition") == "REVIEW"),
                    "rare": sum(1 for r in _latest_results if r.get("result", {}).get("disposition") == "RARE"),
                    "results": _latest_results,
                    "scanning": _scanning_active,
                }
            self.wfile.write(json.dumps(data).encode())
        elif self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress request logs

def run_dashboard(port=DASHBOARD_PORT):
    """Start the dashboard web server."""
    _load_from_json()
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"Dashboard running at http://<Pi-IP>:{port}")
    print(f"Open on your phone/tablet browser (same WiFi)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
        server.server_close()

if __name__ == "__main__":
    run_dashboard()