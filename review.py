import sqlite3
import json
import webbrowser
import http.server
import urllib.parse
import threading
import time
from datetime import datetime
from config import DB_FILE


def format_num(n):
    if not n: return "—"
    n = int(n)
    if n >= 1000000: return f"{n/1000000:.1f}M"
    if n >= 1000:    return f"{n/1000:.1f}K"
    return str(n)


def load_channels():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM channels ORDER BY golden_score DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_stats(channels):
    total    = len(channels)
    golden   = sum(1 for c in channels if c.get("review_status") == "golden")
    pending  = sum(1 for c in channels if c.get("review_status", "pending") == "pending")
    rejected = sum(1 for c in channels if c.get("review_status") == "rejected")
    niches   = len(set(c.get("niche", "") for c in channels if c.get("niche")))

    niche_counts = {}
    for ch in channels:
        n = ch.get("niche", "—")
        if n not in niche_counts:
            niche_counts[n] = {"total": 0, "golden": 0, "pending": 0}
        niche_counts[n]["total"] += 1
        s = ch.get("review_status", "pending")
        if s == "golden":  niche_counts[n]["golden"]  += 1
        if s == "pending": niche_counts[n]["pending"] += 1

    return {
        "total": total, "golden": golden, "pending": pending,
        "rejected": rejected, "niches": niches,
        "niche_counts": niche_counts
    }


def generate_html(channels):
    stats      = get_stats(channels)
    ch_json    = json.dumps(channels)
    stats_json = json.dumps(stats)
    now        = datetime.now().strftime("%Y-%m-%d %H:%M")

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>THE GIANT — Intelligence Platform</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#070710; --bg2:#0d0d1a; --bg3:#12121f; --bg4:#181828;
  --border:#1e1e35; --border2:#252540;
  --accent:#6d5acd; --accent2:#8b76e8;
  --gold:#e8b84b; --gold2:#f5d07a;
  --green:#3dd68c; --red:#e05555; --blue:#4d9de0;
  --text:#d0d0e8; --text2:#8888aa; --text3:#4a4a6a;
  --mono:'IBM Plex Mono',monospace; --sans:'Outfit',sans-serif;
  --radius:10px;
}
*{margin:0;padding:0;box-sizing:border-box;}
html,body{height:100%;overflow:hidden;}
body{background:var(--bg);color:var(--text);font-family:var(--sans);display:flex;}

/* SIDEBAR */
.sidebar{width:220px;min-width:220px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;z-index:10;}
.sidebar-logo{padding:24px 20px 20px;border-bottom:1px solid var(--border);}
.logo-badge{font-family:var(--mono);font-size:.55rem;color:var(--accent2);letter-spacing:3px;text-transform:uppercase;margin-bottom:6px;}
.logo-name{font-size:1.5rem;font-weight:800;color:#fff;letter-spacing:-.5px;}
.logo-sub{font-family:var(--mono);font-size:.58rem;color:var(--text3);margin-top:3px;letter-spacing:1px;}
.sb-section{padding:20px 12px 8px;}
.sb-label{font-family:var(--mono);font-size:.55rem;color:var(--text3);letter-spacing:3px;text-transform:uppercase;padding:0 8px;margin-bottom:6px;}
.nav-item{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:8px;cursor:pointer;font-size:.85rem;font-weight:500;color:var(--text2);transition:all .15s;margin-bottom:2px;border:1px solid transparent;user-select:none;}
.nav-item:hover{background:var(--bg3);color:var(--text);}
.nav-item.active{background:linear-gradient(135deg,#6d5acd18,#4c1d9512);border-color:#6d5acd30;color:#c4b5fd;}
.nav-icon{font-size:1rem;width:18px;text-align:center;flex-shrink:0;}
.nav-badge{margin-left:auto;font-family:var(--mono);font-size:.6rem;background:var(--bg4);border:1px solid var(--border2);color:var(--text2);padding:1px 7px;border-radius:10px;}
.nav-badge.green{background:#3dd68c18;border-color:#3dd68c44;color:var(--green);}
.sb-bottom{margin-top:auto;padding:16px 12px;border-top:1px solid var(--border);}
.sb-time{font-family:var(--mono);font-size:.62rem;color:var(--text3);padding:4px 12px;}

/* MAIN */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;}
.topbar{height:52px;background:var(--bg2);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 28px;gap:16px;flex-shrink:0;}
.tb-title{font-size:.9rem;font-weight:700;color:#fff;}
.tb-sub{font-family:var(--mono);font-size:.65rem;color:var(--text3);}
.tb-right{margin-left:auto;display:flex;align-items:center;gap:10px;}
.tb-stat{font-family:var(--mono);font-size:.68rem;color:var(--text2);background:var(--bg3);border:1px solid var(--border);padding:4px 10px;border-radius:6px;}
.page{flex:1;display:none;overflow:hidden;}
.page.active{display:flex;flex-direction:column;}
#page-overview{overflow-y:auto;}
#page-review{overflow:hidden;}

/* OVERVIEW PAGE */
.ov-header{padding:28px 32px 0;}
.ov-title{font-size:1.4rem;font-weight:700;color:#fff;margin-bottom:4px;}
.ov-sub{font-family:var(--mono);font-size:.68rem;color:var(--text3);}
.kpi-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:16px;padding:24px 32px;}
.kpi{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:20px 22px;position:relative;overflow:hidden;}
.kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--accent);opacity:.6;}
.kpi.gold::before{background:var(--gold);}
.kpi.green::before{background:var(--green);}
.kpi.red::before{background:var(--red);}
.kpi.blue::before{background:var(--blue);}
.kpi-label{font-family:var(--mono);font-size:.58rem;color:var(--text3);letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;}
.kpi-value{font-family:var(--sans);font-size:2rem;font-weight:800;color:#fff;line-height:1;}
.kpi.gold .kpi-value{color:var(--gold);}
.kpi.green .kpi-value{color:var(--green);}
.kpi.red .kpi-value{color:var(--red);}
.kpi.blue .kpi-value{color:var(--blue);}
.kpi-sub{font-family:var(--mono);font-size:.6rem;color:var(--text3);margin-top:6px;}
.section-block{margin:0 32px 28px;}
.section-heading{font-family:var(--mono);font-size:.62rem;color:var(--text3);letter-spacing:3px;text-transform:uppercase;margin-bottom:14px;display:flex;align-items:center;gap:10px;}
.section-heading::after{content:'';flex:1;height:1px;background:var(--border);}
.niche-table{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;width:100%;border-collapse:collapse;}
.niche-table th{background:var(--bg3);padding:10px 16px;font-family:var(--mono);font-size:.6rem;color:var(--text3);letter-spacing:2px;text-transform:uppercase;text-align:left;border-bottom:1px solid var(--border);}
.niche-table td{padding:11px 16px;font-size:.82rem;border-bottom:1px solid var(--border);color:var(--text);}
.niche-table tr:last-child td{border-bottom:none;}
.niche-table tr:hover td{background:var(--bg3);}
.pill{display:inline-block;font-family:var(--mono);font-size:.62rem;padding:2px 8px;border-radius:10px;border:1px solid;}
.pill-gold{background:#e8b84b12;border-color:#e8b84b44;color:var(--gold);}
.pill-green{background:#3dd68c12;border-color:#3dd68c44;color:var(--green);}
.pill-dim{background:#ffffff08;border-color:#ffffff18;color:var(--text3);}
.progress-bar{height:4px;background:var(--bg4);border-radius:2px;overflow:hidden;margin-top:4px;}
.progress-fill{height:100%;background:var(--accent);border-radius:2px;}

/* REVIEW PAGE */
.review-layout{display:flex;flex:1;overflow:hidden;}
.filter-panel{width:258px;min-width:258px;background:var(--bg2);border-right:1px solid var(--border);overflow-y:auto;padding:18px 14px;display:flex;flex-direction:column;gap:14px;}
.filter-title{font-family:var(--mono);font-size:.62rem;color:var(--text3);letter-spacing:3px;text-transform:uppercase;}
.filter-group{background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:13px;}
.fg-label{font-size:.78rem;font-weight:600;color:var(--text);margin-bottom:11px;display:flex;align-items:center;gap:6px;}
.range-row{margin-bottom:11px;}
.range-labels{display:flex;justify-content:space-between;font-family:var(--mono);font-size:.62rem;color:var(--text2);margin-bottom:5px;}
.range-val{color:var(--accent2);font-weight:600;}
input[type=range]{width:100%;height:4px;-webkit-appearance:none;background:var(--border2);border-radius:2px;outline:none;cursor:pointer;margin:3px 0;}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:13px;height:13px;border-radius:50%;background:var(--accent2);border:2px solid var(--bg);cursor:pointer;box-shadow:0 0 5px #6d5acd55;}
.status-pills{display:flex;flex-wrap:wrap;gap:5px;}
.spill{font-family:var(--mono);font-size:.63rem;padding:5px 10px;border-radius:20px;border:1px solid var(--border2);background:var(--bg4);color:var(--text2);cursor:pointer;transition:all .15s;user-select:none;}
.spill:hover{border-color:var(--accent);color:var(--accent2);}
.spill.active{background:#6d5acd18;border-color:var(--accent);color:#c4b5fd;}
.spill.s-gold.active{background:#e8b84b18;border-color:var(--gold);color:var(--gold);}
.spill.s-red.active{background:#e0555518;border-color:var(--red);color:var(--red);}
.niche-pills{display:flex;flex-wrap:wrap;gap:5px;max-height:160px;overflow-y:auto;}
.npill{font-family:var(--mono);font-size:.58rem;padding:3px 8px;border-radius:8px;border:1px solid var(--border2);background:var(--bg4);color:var(--text3);cursor:pointer;transition:all .15s;user-select:none;}
.npill:hover{border-color:var(--accent);color:var(--text2);}
.npill.active{background:#6d5acd18;border-color:var(--accent);color:#c4b5fd;}
.filter-reset{background:transparent;border:1px solid var(--border2);color:var(--text3);padding:8px;border-radius:8px;font-family:var(--mono);font-size:.63rem;cursor:pointer;width:100%;transition:all .15s;letter-spacing:1px;}
.filter-reset:hover{border-color:var(--text3);color:var(--text);}

/* REVIEW CONTENT */
.review-content{flex:1;overflow:hidden;display:flex;flex-direction:column;}
.review-toolbar{padding:13px 18px;border-bottom:1px solid var(--border);background:var(--bg2);display:flex;align-items:center;gap:10px;flex-shrink:0;}
.search-box{background:var(--bg3);border:1px solid var(--border2);color:var(--text);padding:7px 13px;border-radius:8px;font-family:var(--sans);font-size:.82rem;outline:none;width:230px;transition:border-color .15s;}
.search-box:focus{border-color:var(--accent);}
.search-box::placeholder{color:var(--text3);}
.sort-select{background:var(--bg3);border:1px solid var(--border2);color:var(--text);padding:7px 11px;border-radius:8px;font-family:var(--mono);font-size:.68rem;outline:none;cursor:pointer;}
.count-label{font-family:var(--mono);font-size:.65rem;color:var(--text3);margin-left:auto;}
.channel-grid{flex:1;overflow-y:auto;padding:18px;display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:13px;align-content:start;}

/* CARD */
.card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;transition:all .15s;}
.card:hover{border-color:var(--border2);transform:translateY(-1px);}
.card[data-status="golden"]{border-color:#e8b84b28;}
.card[data-status="rejected"]{opacity:.35;}
.card-top{padding:13px 13px 0;display:flex;align-items:flex-start;gap:11px;}
.ch-avatar{width:38px;height:38px;border-radius:50%;background:var(--bg4);border:1px solid var(--border2);object-fit:cover;flex-shrink:0;}
.ch-info{flex:1;min-width:0;}
.ch-name{font-size:.87rem;font-weight:600;color:var(--accent2);text-decoration:none;display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.ch-name:hover{color:#fff;}
.ch-niche{font-family:var(--mono);font-size:.55rem;color:var(--text3);letter-spacing:1px;text-transform:uppercase;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.ch-badge{font-family:var(--mono);font-size:.56rem;padding:2px 7px;border-radius:5px;border:1px solid;flex-shrink:0;}
.badge-pending{background:#ffffff07;border-color:#2a2a45;color:var(--text3);}
.badge-golden{background:#e8b84b10;border-color:#e8b84b40;color:var(--gold);}
.badge-rejected{background:#e0555510;border-color:#e0555540;color:var(--red);}
.card-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border);margin:11px 13px;border-radius:8px;overflow:hidden;border:1px solid var(--border);}
.stat-cell{background:var(--bg3);padding:8px 9px;text-align:center;}
.stat-val{font-size:.86rem;font-weight:700;color:#fff;line-height:1;}
.stat-lbl{font-family:var(--mono);font-size:.52rem;color:var(--text3);margin-top:3px;text-transform:uppercase;letter-spacing:1px;}
.card-meta{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--border);margin:0 13px 11px;border-radius:8px;overflow:hidden;border:1px solid var(--border);}
.meta-cell{background:var(--bg3);padding:7px 9px;text-align:center;}
.meta-val{font-family:var(--mono);font-size:.7rem;color:var(--text2);line-height:1;}
.meta-lbl{font-family:var(--mono);font-size:.5rem;color:var(--text3);margin-top:3px;text-transform:uppercase;}
.card-actions{padding:0 13px 13px;display:flex;gap:5px;}
.act-btn{padding:7px 10px;border-radius:7px;border:1px solid var(--border2);background:var(--bg3);color:var(--text2);font-family:var(--sans);font-size:.74rem;font-weight:600;cursor:pointer;transition:all .12s;flex:1;text-align:center;}
.act-btn:hover{background:var(--bg4);color:var(--text);}
.act-open{background:#4d9de010;border-color:#4d9de030;color:var(--blue);}
.act-open:hover{background:#4d9de020;}
.act-golden{background:#e8b84b10;border-color:#e8b84b30;color:var(--gold);}
.act-golden:hover{background:#e8b84b20;}
.act-reject{background:#e0555510;border-color:#e0555530;color:var(--red);}
.act-reject:hover{background:#e0555520;}
.act-reset{background:transparent;border-color:#2a2a45;color:var(--text3);flex:0;padding:7px 9px;}
.act-reset:hover{border-color:var(--border2);color:var(--text2);}

/* TOAST */
.toast{position:fixed;bottom:22px;right:22px;background:var(--bg3);border:1px solid var(--accent);color:#c4b5fd;padding:9px 16px;border-radius:8px;font-family:var(--mono);font-size:.7rem;opacity:0;transform:translateY(5px);transition:all .2s;z-index:9999;pointer-events:none;}
.toast.show{opacity:1;transform:translateY(0);}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px;}
.empty-state{grid-column:1/-1;text-align:center;padding:60px 20px;color:var(--text3);font-family:var(--mono);font-size:.78rem;}
.empty-icon{font-size:2rem;margin-bottom:10px;}
</style>
</head>
<body>

<div class="sidebar">
  <div class="sidebar-logo">
    <div class="logo-badge">Intelligence System v2</div>
    <div class="logo-name">THE GIANT</div>
    <div class="logo-sub">Discovery · Review · Patterns</div>
  </div>

  <div class="sb-section">
    <div class="sb-label">Platform</div>
    <div class="nav-item active" onclick="showPage('overview',this)">
      <span class="nav-icon">◈</span><span>Overview</span>
    </div>
    <div class="nav-item" onclick="showPage('review',this)">
      <span class="nav-icon">⊞</span><span>Channel Review</span>
      <span class="nav-badge green" id="nav-pending-badge">—</span>
    </div>
  </div>

  <div class="sb-section">
    <div class="sb-label">Coming Soon</div>
    <div class="nav-item" style="opacity:.3;cursor:not-allowed">
      <span class="nav-icon">▶</span><span>Video Scraper</span>
      <span class="nav-badge">P2</span>
    </div>
    <div class="nav-item" style="opacity:.3;cursor:not-allowed">
      <span class="nav-icon">◎</span><span>Pattern Engine</span>
      <span class="nav-badge">P3</span>
    </div>
    <div class="nav-item" style="opacity:.3;cursor:not-allowed">
      <span class="nav-icon">✦</span><span>Title Generator</span>
      <span class="nav-badge">P4</span>
    </div>
  </div>

  <div class="sb-bottom">
    <div class="sb-time" id="clock">—</div>
    <div class="sb-time">Updated """ + now + """</div>
  </div>
</div>

<div class="main">
  <div class="topbar">
    <div>
      <div class="tb-title" id="tb-title">Overview</div>
      <div class="tb-sub"  id="tb-sub">Platform intelligence summary</div>
    </div>
    <div class="tb-right">
      <div class="tb-stat" id="tb-total">—</div>
      <div class="tb-stat" style="color:var(--gold)"   id="tb-golden">—</div>
      <div class="tb-stat" style="color:var(--accent2)" id="tb-pending">—</div>
    </div>
  </div>

  <!-- OVERVIEW PAGE -->
  <div class="page active" id="page-overview">
    <div class="ov-header">
      <div class="ov-title">Intelligence Overview</div>
      <div class="ov-sub">Channel discovery summary · """ + now + """</div>
    </div>
    <div class="kpi-grid">
      <div class="kpi">
        <div class="kpi-label">Total Channels</div>
        <div class="kpi-value" id="kpi-total">""" + str(stats['total']) + """</div>
        <div class="kpi-sub">discovered</div>
      </div>
      <div class="kpi gold">
        <div class="kpi-label">Golden Approved</div>
        <div class="kpi-value" id="kpi-golden">""" + str(stats['golden']) + """</div>
        <div class="kpi-sub">manually verified</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Pending Review</div>
        <div class="kpi-value" id="kpi-pending">""" + str(stats['pending']) + """</div>
        <div class="kpi-sub">awaiting decision</div>
      </div>
      <div class="kpi red">
        <div class="kpi-label">Rejected</div>
        <div class="kpi-value" id="kpi-rejected">""" + str(stats['rejected']) + """</div>
        <div class="kpi-sub">removed</div>
      </div>
      <div class="kpi blue">
        <div class="kpi-label">Niches</div>
        <div class="kpi-value" id="kpi-niches">""" + str(stats['niches']) + """</div>
        <div class="kpi-sub">categories</div>
      </div>
    </div>
    <div class="section-block">
      <div class="section-heading">Niche Breakdown</div>
      <table class="niche-table">
        <thead><tr>
          <th>Niche</th><th>Total</th><th>Golden</th><th>Pending</th><th>Review Progress</th>
        </tr></thead>
        <tbody id="niche-tbody"></tbody>
      </table>
    </div>
  </div>

  <!-- REVIEW PAGE -->
  <div class="page" id="page-review">
    <div class="review-layout">

      <div class="filter-panel">
        <div class="filter-title">Filters</div>

        <div class="filter-group">
          <div class="fg-label">📌 Review Status</div>
          <div class="status-pills">
            <div class="spill active"  onclick="toggleStatus('all',this)">All</div>
            <div class="spill s-gold"  onclick="toggleStatus('golden',this)">★ Golden</div>
            <div class="spill"         onclick="toggleStatus('pending',this)">⏳ Pending</div>
            <div class="spill s-red"   onclick="toggleStatus('rejected',this)">✕ Rejected</div>
          </div>
        </div>

        <div class="filter-group">
          <div class="fg-label">👥 Subscribers</div>
          <div class="range-row">
            <div class="range-labels"><span>Min</span><span class="range-val" id="subs-min-val">0</span></div>
            <input type="range" id="subs-min" min="0" max="500" value="0" oninput="updateRange('subs')">
          </div>
          <div class="range-row" style="margin-bottom:0">
            <div class="range-labels"><span>Max</span><span class="range-val" id="subs-max-val">500K</span></div>
            <input type="range" id="subs-max" min="0" max="500" value="500" oninput="updateRange('subs')">
          </div>
        </div>

        <div class="filter-group">
          <div class="fg-label">⭐ Score</div>
          <div class="range-row">
            <div class="range-labels"><span>Min</span><span class="range-val" id="score-min-val">0</span></div>
            <input type="range" id="score-min" min="0" max="100" value="0" oninput="updateRange('score')">
          </div>
          <div class="range-row" style="margin-bottom:0">
            <div class="range-labels"><span>Max</span><span class="range-val" id="score-max-val">100</span></div>
            <input type="range" id="score-max" min="0" max="100" value="100" oninput="updateRange('score')">
          </div>
        </div>

        <div class="filter-group">
          <div class="fg-label">🤖 Faceless AI %</div>
          <div class="range-row" style="margin-bottom:0">
            <div class="range-labels"><span>Minimum</span><span class="range-val" id="face-min-val">0%</span></div>
            <input type="range" id="face-min" min="0" max="100" value="0" oninput="updateRange('face')">
          </div>
        </div>

        <div class="filter-group">
          <div class="fg-label">🎬 Total Videos</div>
          <div class="range-row">
            <div class="range-labels"><span>Min</span><span class="range-val" id="vids-min-val">0</span></div>
            <input type="range" id="vids-min" min="0" max="200" value="0" oninput="updateRange('vids')">
          </div>
          <div class="range-row" style="margin-bottom:0">
            <div class="range-labels"><span>Max</span><span class="range-val" id="vids-max-val">200+</span></div>
            <input type="range" id="vids-max" min="0" max="200" value="200" oninput="updateRange('vids')">
          </div>
        </div>

        <div class="filter-group">
          <div class="fg-label">📅 Channel Age</div>
          <div class="range-row" style="margin-bottom:0">
            <div class="range-labels"><span>Max Age</span><span class="range-val" id="age-max-val">365d</span></div>
            <input type="range" id="age-max" min="1" max="365" value="365" oninput="updateRange('age')">
          </div>
        </div>

        <div class="filter-group">
          <div class="fg-label">🕐 Last Upload</div>
          <div class="range-row" style="margin-bottom:0">
            <div class="range-labels"><span>Max days ago</span><span class="range-val" id="last-max-val">40d</span></div>
            <input type="range" id="last-max" min="0" max="40" value="40" oninput="updateRange('last')">
          </div>
        </div>

        <div class="filter-group">
          <div class="fg-label">🔥 Recent Views</div>
          <div class="range-row" style="margin-bottom:0">
            <div class="range-labels"><span>Minimum</span><span class="range-val" id="recent-min-val">0</span></div>
            <input type="range" id="recent-min" min="0" max="100" value="0" oninput="updateRange('recent')">
          </div>
        </div>

        <div class="filter-group">
          <div class="fg-label">🤖 Faceless Confirmed</div>
          <div class="status-pills">
            <div class="spill active" onclick="toggleFaceless('all',this)">All</div>
            <div class="spill s-gold" onclick="toggleFaceless('yes',this)">✓ Faceless Only</div>
            <div class="spill s-red"  onclick="toggleFaceless('no',this)">✕ Not Faceless</div>
          </div>
        </div>

        <div class="filter-group">
          <div class="fg-label">🗂 Niche</div>
          <div class="niche-pills" id="niche-pills"></div>
        </div>

        <button class="filter-reset" onclick="resetFilters()">↺ Reset All Filters</button>
      </div>

      <div class="review-content">
        <div class="review-toolbar">
          <input class="search-box" type="text" id="search-input"
                 placeholder="🔍 Search channel name..." oninput="applyFilters()">
          <select class="sort-select" id="sort-select" onchange="applyFilters()">
            <option value="score">Score ↓</option>
            <option value="subs">Subscribers ↓</option>
            <option value="age_asc">Newest Channel</option>
            <option value="age_desc">Oldest Channel</option>
            <option value="videos">Most Videos</option>
            <option value="faceless">Faceless % ↓</option>
          </select>
          <div class="count-label" id="count-label">—</div>
        </div>
        <div class="channel-grid" id="channel-grid"></div>
      </div>

    </div>
  </div>

</div>

<div class="toast" id="toast"></div>

<script>
const ALL = """ + ch_json + """;
const ST  = """ + stats_json + """;

let activeStatus  = 'all';
let activeNiches  = new Set();
let facelessFilter = 'all';

function init() {
  buildNicheTable();
  buildNichePills();
  updateTopbar();
  document.getElementById('nav-pending-badge').textContent = ST.pending;
  setInterval(() => {
    document.getElementById('clock').textContent =
      new Date().toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  }, 1000);
}

function showPage(page, el) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  el.classList.add('active');
  const t = {overview:['Overview','Platform summary'],review:['Channel Review','Browse and approve channels']};
  document.getElementById('tb-title').textContent = t[page][0];
  document.getElementById('tb-sub').textContent   = t[page][1];
  if (page === 'review') applyFilters();
}

function updateTopbar() {
  const g = ALL.filter(c=>c.review_status==='golden').length;
  const p = ALL.filter(c=>(c.review_status||'pending')==='pending').length;
  document.getElementById('tb-total').textContent   = 'Total: ' + ALL.length;
  document.getElementById('tb-golden').textContent  = 'Golden: ' + g;
  document.getElementById('tb-pending').textContent = 'Pending: ' + p;
  document.getElementById('nav-pending-badge').textContent = p;
  document.getElementById('kpi-golden').textContent  = g;
  document.getElementById('kpi-pending').textContent = p;
  document.getElementById('kpi-rejected').textContent = ALL.filter(c=>c.review_status==='rejected').length;
}

function buildNicheTable() {
  const nc     = ST.niche_counts;
  const sorted = Object.entries(nc).sort((a,b) => b[1].total - a[1].total);
  document.getElementById('niche-tbody').innerHTML = sorted.map(([n, d]) => {
    const pct = d.total > 0 ? Math.round((d.golden/d.total)*100) : 0;
    return `<tr>
      <td style="font-weight:600;color:var(--text)">${n}</td>
      <td style="font-family:var(--mono);font-size:.8rem">${d.total}</td>
      <td>${d.golden>0 ? `<span class="pill pill-gold">${d.golden}</span>` : `<span class="pill pill-dim">0</span>`}</td>
      <td>${d.pending>0 ? `<span class="pill pill-green">${d.pending}</span>` : `<span class="pill pill-dim">0</span>`}</td>
      <td style="min-width:120px"><div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div></td>
    </tr>`;
  }).join('');
}

function buildNichePills() {
  const niches = Object.keys(ST.niche_counts).sort();
  document.getElementById('niche-pills').innerHTML = niches.map(n =>
    `<div class="npill" onclick="toggleNiche('${n}',this)" data-niche="${n}">${n}</div>`
  ).join('');
}

function toggleStatus(s, el) {
  activeStatus = s;
  document.querySelectorAll('.spill').forEach(x => x.classList.remove('active'));
  el.classList.add('active');
  applyFilters();
}

function toggleNiche(n, el) {
  if (activeNiches.has(n)) { activeNiches.delete(n); el.classList.remove('active'); }
  else { activeNiches.add(n); el.classList.add('active'); }
  applyFilters();
}

function sliderToSubs(v) { return v * 1000; }
function fmtSubs(v) {
  if (v===0) return '0'; if (v>=1000000) return (v/1000000).toFixed(1)+'M';
  if (v>=1000) return (v/1000).toFixed(0)+'K'; return v;
}

function updateRange(type) {
  if (type==='subs') {
    document.getElementById('subs-min-val').textContent = fmtSubs(sliderToSubs(+document.getElementById('subs-min').value));
    document.getElementById('subs-max-val').textContent = fmtSubs(sliderToSubs(+document.getElementById('subs-max').value));
  }
  if (type==='score') {
    document.getElementById('score-min-val').textContent = document.getElementById('score-min').value;
    document.getElementById('score-max-val').textContent = document.getElementById('score-max').value;
  }
  if (type==='face') {
    document.getElementById('face-min-val').textContent = document.getElementById('face-min').value + '%';
  }
  if (type==='vids') {
    const mx = +document.getElementById('vids-max').value;
    document.getElementById('vids-min-val').textContent = document.getElementById('vids-min').value;
    document.getElementById('vids-max-val').textContent = mx>=200 ? '200+' : mx;
  }
  if (type==='age') {
    document.getElementById('age-max-val').textContent = document.getElementById('age-max').value + 'd';
  }
  if (type==='last') {
    const v = +document.getElementById('last-max').value;
    document.getElementById('last-max-val').textContent = v>=40 ? 'Any' : v+'d';
  }
  if (type==='recent') {
    const v = +document.getElementById('recent-min').value;
    // slider 0-100 maps to 0-100K views
    const views = v * 1000;
    document.getElementById('recent-min-val').textContent = v===0 ? '0' : fmtSubs(views);
  }
  applyFilters();
}

function toggleFaceless(val, el) {
  facelessFilter = val;
  // only reset pills inside that specific filter-group
  el.closest('.filter-group').querySelectorAll('.spill').forEach(s=>s.classList.remove('active'));
  el.classList.add('active');
  applyFilters();
}

function resetFilters() {
  activeStatus   = 'all';
  activeNiches.clear();
  facelessFilter = 'all';
  document.querySelectorAll('.spill').forEach(s=>s.classList.remove('active'));
  // re-activate first pill in each group
  document.querySelectorAll('.filter-group').forEach(g=>{
    const first = g.querySelector('.spill');
    if (first) first.classList.add('active');
  });
  document.querySelectorAll('.npill').forEach(p=>p.classList.remove('active'));
  document.getElementById('subs-min').value=0;   document.getElementById('subs-max').value=500;
  document.getElementById('score-min').value=0;  document.getElementById('score-max').value=100;
  document.getElementById('face-min').value=0;
  document.getElementById('vids-min').value=0;   document.getElementById('vids-max').value=200;
  document.getElementById('age-max').value=365;
  document.getElementById('last-max').value=40;
  document.getElementById('recent-min').value=0;
  document.getElementById('search-input').value='';
  ['subs','score','face','vids','age','last','recent'].forEach(t=>updateRange(t));
  applyFilters();
}

function applyFilters() {
  const search    = document.getElementById('search-input').value.toLowerCase();
  const sort      = document.getElementById('sort-select').value;
  const subsMin   = sliderToSubs(+document.getElementById('subs-min').value);
  const subsMax   = sliderToSubs(+document.getElementById('subs-max').value);
  const scoreMin  = +document.getElementById('score-min').value;
  const scoreMax  = +document.getElementById('score-max').value;
  const faceMin   = +document.getElementById('face-min').value;
  const vidsMin   = +document.getElementById('vids-min').value;
  const vidsMax   = +document.getElementById('vids-max').value;
  const ageMax    = +document.getElementById('age-max').value;
  const lastMax   = +document.getElementById('last-max').value;
  const recentMin = +document.getElementById('recent-min').value * 1000;

  let filtered = ALL.filter(ch => {
    const status    = ch.review_status||'pending';
    const subs      = ch.subscribers||0;
    const score     = ch.golden_score||0;
    const face      = ch.faceless_score||0;
    const vids      = ch.video_count||0;
    const age       = ch.channel_age_days||0;
    const last      = ch.last_video_days!=null ? ch.last_video_days : 999;
    const recent    = ch.recent_views||0;
    const isFaceless = ch.is_faceless||0;
    const name      = (ch.channel_name||'').toLowerCase();

    if (activeStatus!=='all' && status!==activeStatus) return false;
    if (activeNiches.size>0 && !activeNiches.has(ch.niche||'')) return false;
    if (search && !name.includes(search)) return false;
    if (subs<subsMin || subs>subsMax) return false;
    if (score<scoreMin || score>scoreMax) return false;
    if (face<faceMin) return false;
    if (vids<vidsMin) return false;
    if (vidsMax<200 && vids>vidsMax) return false;
    if (age>ageMax) return false;
    if (lastMax<40 && last>lastMax) return false;
    if (recentMin>0 && recent<recentMin) return false;
    if (facelessFilter==='yes' && !isFaceless) return false;
    if (facelessFilter==='no'  &&  isFaceless) return false;
    return true;
  });

  filtered.sort((a,b) => {
    if (sort==='score')    return (b.golden_score||0)-(a.golden_score||0);
    if (sort==='subs')     return (b.subscribers||0)-(a.subscribers||0);
    if (sort==='age_asc')  return (a.channel_age_days||0)-(b.channel_age_days||0);
    if (sort==='age_desc') return (b.channel_age_days||0)-(a.channel_age_days||0);
    if (sort==='videos')   return (b.video_count||0)-(a.video_count||0);
    if (sort==='faceless') return (b.faceless_score||0)-(a.faceless_score||0);
    return 0;
  });

  document.getElementById('count-label').textContent = filtered.length + ' channels';
  renderCards(filtered);
}

function renderCards(channels) {
  const grid = document.getElementById('channel-grid');
  if (!channels.length) {
    grid.innerHTML = '<div class="empty-state"><div class="empty-icon">◎</div>No channels match your filters.</div>';
    return;
  }
  grid.innerHTML = channels.map(ch => {
    const cid   = ch.channel_id||'';
    const name  = ch.channel_name||'Unknown';
    const url   = ch.channel_url||'https://www.youtube.com/channel/'+cid;
    const subs  = fmt(ch.subscribers);
    const score = ch.golden_score||0;
    const age   = ch.channel_age_days!=null ? ch.channel_age_days+'d' : '?';
    const vids  = ch.video_count||0;
    const last  = ch.last_video_days!=null ? ch.last_video_days+'d ago' : '?';
    const face  = ch.faceless_score||0;
    const rec   = fmt(ch.recent_views);
    const st    = ch.review_status||'pending';
    const sc    = score>=60?'var(--green)':score>=40?'var(--gold)':'var(--text2)';
    const fc    = face>=70?'var(--green)':face>=40?'var(--gold)':'var(--red)';
    const badges = {pending:'<span class="ch-badge badge-pending">⏳ Pending</span>',
                    golden:'<span class="ch-badge badge-golden">★ Golden</span>',
                    rejected:'<span class="ch-badge badge-rejected">✕ Rejected</span>'};
    return `<div class="card" id="card-${cid}" data-status="${st}">
      <div class="card-top">
        <img class="ch-avatar" src="https://yt3.googleusercontent.com/channel/${cid}"
             onerror="this.style.display='none'" alt="">
        <div class="ch-info">
          <a class="ch-name" href="${url}" target="_blank">${name}</a>
          <div class="ch-niche">${ch.niche||'—'}</div>
        </div>
        ${badges[st]||badges.pending}
      </div>
      <div class="card-stats">
        <div class="stat-cell"><div class="stat-val">${subs}</div><div class="stat-lbl">Subs</div></div>
        <div class="stat-cell"><div class="stat-val" style="color:${sc}">${score}</div><div class="stat-lbl">Score</div></div>
        <div class="stat-cell"><div class="stat-val">${vids}</div><div class="stat-lbl">Videos</div></div>
        <div class="stat-cell"><div class="stat-val" style="color:${fc}">${face}%</div><div class="stat-lbl">Faceless</div></div>
      </div>
      <div class="card-meta">
        <div class="meta-cell"><div class="meta-val">${age}</div><div class="meta-lbl">Age</div></div>
        <div class="meta-cell"><div class="meta-val">${last}</div><div class="meta-lbl">Last Upload</div></div>
        <div class="meta-cell"><div class="meta-val">${rec}</div><div class="meta-lbl">Recent Views</div></div>
      </div>
      <div class="card-actions">
        <button class="act-btn act-open"   onclick="window.open('${url}','_blank')">▶ Open</button>
        <button class="act-btn act-golden" onclick="setStatus('${cid}','golden')">★ Golden</button>
        <button class="act-btn act-reject" onclick="setStatus('${cid}','rejected')">✕ Reject</button>
        <button class="act-btn act-reset"  onclick="setStatus('${cid}','pending')">↺</button>
      </div>
    </div>`;
  }).join('');
}

function fmt(n) {
  if (!n) return '—'; n=parseInt(n);
  if (n>=1000000) return (n/1000000).toFixed(1)+'M';
  if (n>=1000)    return (n/1000).toFixed(1)+'K';
  return n;
}

async function setStatus(cid, status) {
  try {
    const r = await fetch('http://localhost:7842/update?id='+cid+'&status='+status);
    const d = await r.json();
    if (d.ok) {
      const ch = ALL.find(c=>c.channel_id===cid);
      if (ch) { ch.review_status = status; ch.is_golden = status==='golden'?1:0; }
      const card = document.getElementById('card-'+cid);
      if (card) card.dataset.status = status;
      updateTopbar();
      buildNicheTable();
      const m = {golden:'★ Marked Golden', rejected:'✕ Rejected', pending:'↺ Reset'};
      showToast(m[status]||'Updated');
      applyFilters();
    }
  } catch(e) { showToast('⚠ Server offline — run review.py'); }
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'), 2400);
}

init();
</script>
</body>
</html>"""

# ================================================================
#  REVIEW API SERVER
# ================================================================
def run_review_server():
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            if parsed.path == "/update":
                cid    = params.get("id",     [""])[0]
                status = params.get("status", ["pending"])[0]
                if status not in ("pending","golden","rejected"):
                    self._j({"ok":False}); return
                conn = sqlite3.connect(DB_FILE)
                conn.execute(
                    "UPDATE channels SET review_status=?, is_golden=? WHERE channel_id=?",
                    (status, 1 if status=="golden" else 0, cid)
                )
                conn.commit()
                c = conn.cursor()
                c.execute("SELECT channel_name FROM channels WHERE channel_id=?", (cid,))
                row = c.fetchone(); conn.close()
                name = row[0] if row else cid
                icon = "★ GOLDEN" if status=="golden" else "✕ Reject" if status=="rejected" else "↺ Reset"
                print(f"  {icon:10} → {name}")
                self._j({"ok":True,"channel":name,"status":status})
            else:
                self._j({"ok":False})

        def _j(self, data):
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",len(body))
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            self.wfile.write(body)

    http.server.HTTPServer(("localhost",7842), Handler).serve_forever()


# ================================================================
#  MAIN
# ================================================================
if __name__ == "__main__":
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.execute("ALTER TABLE channels ADD COLUMN review_status TEXT DEFAULT 'pending'")
        conn.commit()
    except: pass
    conn.close()

    channels = load_channels()
    print("\n" + "="*52)
    print("  THE GIANT — Intelligence Platform")
    print("="*52)

    if not channels:
        print("\n  No channels. Run discovery first.")
        exit()

    html = generate_html(channels)
    with open("review.html","w",encoding="utf-8") as f:
        f.write(html)

    s = get_stats(channels)
    print(f"\n  Total: {s['total']}  Golden: {s['golden']}  Pending: {s['pending']}")
    print(f"\n  Dashboard → review.html")
    print(f"  API       → localhost:7842")
    print(f"  Press Ctrl+C to stop\n")

    threading.Thread(target=run_review_server, daemon=True).start()
    webbrowser.open("review.html")

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Stopped.")
