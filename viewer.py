import sqlite3
from datetime import datetime
from config import DB_FILE


def load_data():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM channels ORDER BY golden_score DESC, subscribers DESC")
    channels = [dict(row) for row in c.fetchall()]

    c.execute("SELECT COUNT(*) FROM channels")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM channels WHERE is_golden=1")
    golden_count = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT niche) FROM channels")
    niche_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM keywords")
    keyword_count = c.fetchone()[0]

    c.execute('''SELECT niche, COUNT(*) as total, SUM(is_golden) as golden
                 FROM channels GROUP BY niche ORDER BY golden DESC''')
    niches = [dict(row) for row in c.fetchall()]

    # Top golden channels for spotlight
    c.execute('''SELECT channel_name, channel_url, golden_score, subscribers,
                        video_count, channel_age_days, last_video_days, niche, faceless_score
                 FROM channels WHERE is_golden=1
                 ORDER BY golden_score DESC LIMIT 5''')
    top_golden = [dict(row) for row in c.fetchall()]

    # Score distribution
    c.execute("SELECT COUNT(*) FROM channels WHERE golden_score >= 55")
    s_gold = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM channels WHERE golden_score >= 35 AND golden_score < 55")
    s_prom = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM channels WHERE golden_score < 35")
    s_reg = c.fetchone()[0]

    try:
        c.execute("SELECT COUNT(*) FROM title_patterns")
        tp_count = c.fetchone()[0]
    except Exception:
        tp_count = 0

    conn.close()
    return channels, total, golden_count, niche_count, keyword_count, niches, top_golden, s_gold, s_prom, s_reg, tp_count


def generate_html(channels, total, golden_count, niche_count, keyword_count,
                  niches, top_golden, s_gold, s_prom, s_reg, tp_count):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Niche filter buttons
    niche_btns = ""
    for n in niches:
        nm  = n["niche"]
        g   = n["golden"] or 0
        niche_btns += f'<button class="niche-btn" data-niche="{nm}" onclick="filterNiche(this)">{nm.title()} <span class="nbadge">{g}</span></button>\n'

    # Top golden spotlight cards
    spotlight = ""
    for ch in top_golden:
        age  = ch.get("channel_age_days")
        last = ch.get("last_video_days")
        subs = ch.get("subscribers") or 0
        vids = ch.get("video_count") or 0
        sc   = ch.get("golden_score") or 0
        nm   = ch.get("channel_name") or ""
        url  = ch.get("channel_url") or "#"
        ni   = (ch.get("niche") or "").title()
        age_str  = f"{age}d"  if age  is not None else "?"
        last_str = f"{last}d" if last is not None else "?"
        subs_str = f"{subs/1000:.1f}K" if subs < 1000000 else f"{subs/1000000:.1f}M"
        spotlight += f"""
        <a href="{url}" target="_blank" class="spotlight-card">
          <div class="sc-score">{sc}</div>
          <div class="sc-name">{nm}</div>
          <div class="sc-niche">{ni}</div>
          <div class="sc-stats">
            <span><i class="ic">👥</i>{subs_str}</span>
            <span><i class="ic">🎬</i>{vids} vids</span>
            <span><i class="ic">📅</i>{age_str} old</span>
            <span><i class="ic">⚡</i>{last_str} ago</span>
          </div>
        </a>"""

    # Main table rows
    rows = ""
    for ch in channels:
        score     = ch.get("golden_score") or 0
        is_golden = ch.get("is_golden") or 0
        age       = ch.get("channel_age_days")
        last      = ch.get("last_video_days")
        subs      = ch.get("subscribers") or 0
        videos    = ch.get("video_count") or 0
        name      = ch.get("channel_name") or ""
        url       = ch.get("channel_url") or "#"
        keyword   = ch.get("discovered_via") or ""
        niche     = ch.get("niche") or ""
        fs        = ch.get("faceless_score") or 0

        # Views per video
        total_views = ch.get("total_views") or 0
        vpv = int(total_views / max(videos, 1)) if videos > 0 else 0
        if vpv >= 1000000:
            vpv_str = f"{vpv/1000000:.1f}M"
        elif vpv >= 1000:
            vpv_str = f"{vpv/1000:.0f}K"
        else:
            vpv_str = str(vpv)

        if is_golden:
            row_class = "row-gold"
            badge     = '<span class="badge badge-gold">⭐ GOLDEN</span>'
        elif score >= 35:
            row_class = "row-prom"
            badge     = '<span class="badge badge-prom">▲ PROMISING</span>'
        else:
            row_class = "row-reg"
            badge     = '<span class="badge badge-reg">◦ Regular</span>'

        age_str  = f"{age}d"  if age  is not None else "—"
        last_str = f"{last}d" if last is not None else "—"

        if score >= 55:
            score_class = "score-gold"
        elif score >= 35:
            score_class = "score-prom"
        else:
            score_class = "score-reg"

        subs_fmt = f"{subs:,}"

        # Faceless bar width
        fs_w = min(fs, 100)

        rows += f"""<tr class="{row_class}" data-niche="{niche}" data-golden="{is_golden}" data-score="{score}">
  <td>{badge}</td>
  <td class="td-name"><a href="{url}" target="_blank" class="ch-link">{name}</a></td>
  <td><span class="{score_class} score-val">{score}</span></td>
  <td class="td-mono">{age_str}</td>
  <td class="td-mono">{last_str}</td>
  <td class="td-mono">{subs_fmt}</td>
  <td class="td-mono">{videos}</td>
  <td class="td-vpv">{vpv_str}</td>
  <td><div class="fbar"><div class="fbar-fill" style="width:{fs_w}%"></div><span class="fbar-num">{fs}%</span></div></td>
  <td class="td-niche">{niche}</td>
  <td class="td-kw">{keyword}</td>
</tr>"""

    golden_pct = round((golden_count / max(total, 1)) * 100, 1)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>THE GIANT — Intelligence Database</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
/* ── RESET & BASE ───────────────────────────────────────── */
*, *::before, *::after {{ margin:0; padding:0; box-sizing:border-box; }}
:root {{
  --bg:        #050508;
  --bg2:       #08080f;
  --bg3:       #0c0c18;
  --panel:     #0e0e1c;
  --panel2:    #12122a;
  --border:    rgba(255,255,255,0.06);
  --border2:   rgba(120,80,255,0.2);
  --gold:      #f5c518;
  --gold2:     #ffd770;
  --prom:      #3b9eff;
  --prom2:     #80c4ff;
  --accent:    #8855ff;
  --accent2:   #bb88ff;
  --red:       #ff4466;
  --green:     #00e887;
  --text:      #c8c8d8;
  --text2:     #6868a0;
  --text3:     #3a3a60;
  --mono:      'Space Mono', monospace;
  --sans:      'Syne', sans-serif;
}}
html {{ scroll-behavior: smooth; }}
body {{
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  min-height: 100vh;
  overflow-x: hidden;
}}

/* ── BACKGROUND GRID ────────────────────────────────────── */
body::before {{
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(136,85,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(136,85,255,0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}}

/* ── SIDEBAR ────────────────────────────────────────────── */
.sidebar {{
  position: fixed;
  left: 0; top: 0; bottom: 0;
  width: 220px;
  background: var(--bg2);
  border-right: 1px solid var(--border);
  z-index: 100;
  display: flex;
  flex-direction: column;
  padding: 0;
}}
.sidebar-logo {{
  padding: 28px 24px 20px;
  border-bottom: 1px solid var(--border);
}}
.sidebar-logo .logo-text {{
  font-size: 1.5em;
  font-weight: 800;
  letter-spacing: 3px;
  color: #fff;
}}
.sidebar-logo .logo-text em {{
  color: var(--accent);
  font-style: normal;
}}
.sidebar-logo .logo-sub {{
  font-family: var(--mono);
  font-size: 0.62em;
  color: var(--text3);
  margin-top: 4px;
  letter-spacing: 2px;
  text-transform: uppercase;
}}
.sidebar-nav {{
  flex: 1;
  padding: 16px 0;
  overflow-y: auto;
}}
.nav-section {{
  padding: 8px 16px 4px;
  font-size: 0.6em;
  letter-spacing: 2px;
  color: var(--text3);
  text-transform: uppercase;
  margin-top: 8px;
}}
.nav-btn {{
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 20px;
  background: none;
  border: none;
  color: var(--text2);
  font-family: var(--sans);
  font-size: 0.85em;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
  border-left: 2px solid transparent;
}}
.nav-btn:hover, .nav-btn.active {{
  color: #fff;
  background: rgba(136,85,255,0.08);
  border-left-color: var(--accent);
}}
.nav-btn .ni {{ font-size: 1.1em; }}
.sidebar-footer {{
  padding: 16px 20px;
  border-top: 1px solid var(--border);
  font-family: var(--mono);
  font-size: 0.62em;
  color: var(--text3);
  line-height: 1.8;
}}
.status-dot {{
  display: inline-block;
  width: 6px; height: 6px;
  background: var(--green);
  border-radius: 50%;
  margin-right: 6px;
  animation: pulse 2s infinite;
}}
@keyframes pulse {{
  0%,100% {{ opacity:1; }}
  50% {{ opacity:0.3; }}
}}

/* ── MAIN CONTENT ───────────────────────────────────────── */
.main {{
  margin-left: 220px;
  min-height: 100vh;
  position: relative;
  z-index: 1;
}}

/* ── TOP BAR ────────────────────────────────────────────── */
.topbar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  border-bottom: 1px solid var(--border);
  background: rgba(5,5,8,0.8);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 50;
}}
.topbar-title {{
  font-size: 0.8em;
  color: var(--text2);
  font-family: var(--mono);
  letter-spacing: 1px;
}}
.topbar-title span {{ color: var(--accent2); }}
.topbar-right {{
  display: flex;
  align-items: center;
  gap: 20px;
}}
.search-wrap {{
  position: relative;
}}
.search-wrap input {{
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-family: var(--mono);
  font-size: 0.8em;
  padding: 8px 14px 8px 36px;
  width: 240px;
  outline: none;
  transition: border-color 0.2s;
}}
.search-wrap input:focus {{ border-color: var(--accent); }}
.search-wrap input::placeholder {{ color: var(--text3); }}
.search-icon {{
  position: absolute;
  left: 12px; top: 50%;
  transform: translateY(-50%);
  color: var(--text3);
  font-size: 0.85em;
  pointer-events: none;
}}
.time-badge {{
  font-family: var(--mono);
  font-size: 0.72em;
  color: var(--text3);
  background: var(--panel);
  border: 1px solid var(--border);
  padding: 6px 12px;
  border-radius: 6px;
}}

/* ── CONTENT SECTIONS ───────────────────────────────────── */
.content {{ padding: 28px 32px 60px; }}

/* ── SECTION HEADER ─────────────────────────────────────── */
.section-header {{
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 18px;
}}
.section-title {{
  font-size: 1em;
  font-weight: 700;
  color: #fff;
  letter-spacing: 2px;
  text-transform: uppercase;
}}
.section-line {{
  flex: 1;
  height: 1px;
  background: var(--border);
}}
.section-count {{
  font-family: var(--mono);
  font-size: 0.72em;
  color: var(--text3);
}}

/* ── STATS GRID ─────────────────────────────────────────── */
.stats-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 14px;
  margin-bottom: 32px;
}}
.stat-card {{
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px 22px;
  position: relative;
  overflow: hidden;
  transition: border-color 0.2s, transform 0.2s;
}}
.stat-card:hover {{
  border-color: var(--border2);
  transform: translateY(-2px);
}}
.stat-card::before {{
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--accent);
}}
.stat-card.gold::before {{ background: var(--gold); }}
.stat-card.blue::before {{ background: var(--prom); }}
.stat-card.green::before {{ background: var(--green); }}
.stat-card.red::before {{ background: var(--red); }}
.stat-val {{
  font-family: var(--mono);
  font-size: 2em;
  font-weight: 700;
  color: #fff;
  line-height: 1;
}}
.stat-val.gold {{ color: var(--gold); }}
.stat-val.blue {{ color: var(--prom); }}
.stat-val.green {{ color: var(--green); }}
.stat-label {{
  font-size: 0.68em;
  color: var(--text3);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-top: 6px;
}}
.stat-sub {{
  font-family: var(--mono);
  font-size: 0.72em;
  color: var(--text2);
  margin-top: 8px;
}}
.stat-icon {{
  position: absolute;
  right: 18px; top: 18px;
  font-size: 1.4em;
  opacity: 0.15;
}}

/* ── SPOTLIGHT ROW ──────────────────────────────────────── */
.spotlight-row {{
  display: flex;
  gap: 14px;
  margin-bottom: 32px;
  overflow-x: auto;
  padding-bottom: 4px;
}}
.spotlight-row::-webkit-scrollbar {{ height: 3px; }}
.spotlight-row::-webkit-scrollbar-track {{ background: transparent; }}
.spotlight-row::-webkit-scrollbar-thumb {{ background: var(--accent); border-radius: 2px; }}
.spotlight-card {{
  flex: 0 0 200px;
  background: linear-gradient(135deg, var(--panel), var(--panel2));
  border: 1px solid var(--border2);
  border-radius: 12px;
  padding: 18px;
  text-decoration: none;
  transition: all 0.2s;
  position: relative;
  overflow: hidden;
}}
.spotlight-card::before {{
  content: '';
  position: absolute;
  top: -40px; right: -40px;
  width: 100px; height: 100px;
  background: radial-gradient(circle, rgba(136,85,255,0.15), transparent 70%);
}}
.spotlight-card:hover {{
  border-color: var(--accent);
  transform: translateY(-3px);
  box-shadow: 0 8px 32px rgba(136,85,255,0.2);
}}
.sc-score {{
  font-family: var(--mono);
  font-size: 2em;
  font-weight: 700;
  color: var(--gold);
  line-height: 1;
}}
.sc-name {{
  font-size: 0.88em;
  font-weight: 700;
  color: #fff;
  margin: 8px 0 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.sc-niche {{
  font-size: 0.68em;
  color: var(--accent2);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 12px;
}}
.sc-stats {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}}
.sc-stats span {{
  font-family: var(--mono);
  font-size: 0.65em;
  color: var(--text2);
  background: rgba(255,255,255,0.04);
  padding: 2px 7px;
  border-radius: 4px;
  white-space: nowrap;
}}
.ic {{ margin-right: 3px; }}

/* ── FILTER BAR ─────────────────────────────────────────── */
.filter-bar {{
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}}
.filter-label {{
  font-family: var(--mono);
  font-size: 0.68em;
  color: var(--text3);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-right: 4px;
}}
.filter-btn {{
  background: var(--panel);
  border: 1px solid var(--border);
  color: var(--text2);
  padding: 6px 14px;
  border-radius: 20px;
  font-family: var(--sans);
  font-size: 0.78em;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}}
.filter-btn:hover {{
  border-color: var(--accent);
  color: var(--accent2);
}}
.filter-btn.active {{
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}}
.filter-btn.f-gold.active {{ background: var(--gold); border-color: var(--gold); color: #000; }}
.filter-btn.f-prom.active {{ background: var(--prom); border-color: var(--prom); color: #fff; }}
.niche-btn {{
  background: var(--panel);
  border: 1px solid var(--border);
  color: var(--text2);
  padding: 5px 12px;
  border-radius: 20px;
  font-family: var(--sans);
  font-size: 0.73em;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}}
.niche-btn:hover {{ border-color: var(--accent2); color: var(--accent2); }}
.niche-btn.active {{ background: rgba(136,85,255,0.15); border-color: var(--accent); color: var(--accent2); }}
.nbadge {{
  background: rgba(245,197,24,0.15);
  color: var(--gold);
  padding: 1px 5px;
  border-radius: 5px;
  font-size: 0.85em;
  margin-left: 2px;
}}

/* ── TABLE ──────────────────────────────────────────────── */
.table-wrap {{
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}}
.table-toolbar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--bg3);
}}
.table-toolbar-left {{
  font-family: var(--mono);
  font-size: 0.72em;
  color: var(--text2);
}}
.table-toolbar-left span {{ color: #fff; font-weight: 700; }}
.sort-btns {{
  display: flex;
  gap: 6px;
}}
.sort-btn {{
  background: none;
  border: 1px solid var(--border);
  color: var(--text3);
  padding: 4px 10px;
  border-radius: 5px;
  font-family: var(--mono);
  font-size: 0.68em;
  cursor: pointer;
  transition: all 0.15s;
}}
.sort-btn:hover, .sort-btn.active {{
  border-color: var(--accent);
  color: var(--accent2);
}}
.tbl-outer {{ overflow-x: auto; max-height: 640px; overflow-y: auto; }}
.tbl-outer::-webkit-scrollbar {{ width: 5px; height: 5px; }}
.tbl-outer::-webkit-scrollbar-track {{ background: var(--bg2); }}
.tbl-outer::-webkit-scrollbar-thumb {{ background: var(--accent); border-radius: 3px; }}
table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.84em;
}}
thead tr {{
  background: var(--bg3);
  position: sticky;
  top: 0;
  z-index: 10;
}}
thead th {{
  padding: 11px 14px;
  text-align: left;
  font-family: var(--mono);
  font-size: 0.68em;
  font-weight: 400;
  color: var(--text3);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  white-space: nowrap;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  user-select: none;
  transition: color 0.15s;
}}
thead th:hover {{ color: var(--accent2); }}
tbody tr {{
  border-bottom: 1px solid rgba(255,255,255,0.03);
  transition: background 0.1s;
}}
tbody tr:hover {{ background: rgba(136,85,255,0.06) !important; }}
tbody td {{
  padding: 10px 14px;
  vertical-align: middle;
  white-space: nowrap;
}}
.row-gold {{ background: rgba(245,197,24,0.03); }}
.row-prom {{ background: rgba(59,158,255,0.02); }}
.row-reg  {{ background: transparent; }}

/* Badges */
.badge {{
  display: inline-block;
  padding: 3px 9px;
  border-radius: 6px;
  font-size: 0.7em;
  font-weight: 700;
  letter-spacing: 0.5px;
  white-space: nowrap;
}}
.badge-gold {{ background: rgba(245,197,24,0.12); color: var(--gold); border: 1px solid rgba(245,197,24,0.3); }}
.badge-prom {{ background: rgba(59,158,255,0.12); color: var(--prom2); border: 1px solid rgba(59,158,255,0.3); }}
.badge-reg  {{ background: rgba(255,255,255,0.04); color: var(--text3); border: 1px solid var(--border); }}

/* Score */
.score-val {{
  font-family: var(--mono);
  font-weight: 700;
  font-size: 1em;
}}
.score-gold {{ color: var(--gold); }}
.score-prom {{ color: var(--prom2); }}
.score-reg  {{ color: var(--text3); }}

/* Channel link */
.ch-link {{
  color: var(--text);
  text-decoration: none;
  font-weight: 600;
  transition: color 0.15s;
}}
.ch-link:hover {{ color: var(--accent2); }}

/* Mono cells */
.td-mono {{
  font-family: var(--mono);
  font-size: 0.85em;
  color: var(--text2);
}}
.td-vpv {{
  font-family: var(--mono);
  font-size: 0.85em;
  color: var(--green);
  font-weight: 700;
}}
.td-niche {{ color: var(--accent2); font-size: 0.8em; }}
.td-kw {{ color: var(--text3); font-size: 0.75em; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }}

/* Faceless bar */
.fbar {{
  width: 80px;
  height: 5px;
  background: rgba(255,255,255,0.06);
  border-radius: 3px;
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}}
.fbar-fill {{
  position: absolute;
  left: 0; top: 0; bottom: 0;
  background: linear-gradient(90deg, var(--accent), var(--accent2));
  border-radius: 3px;
  transition: width 0.3s;
}}
.fbar-num {{
  font-family: var(--mono);
  font-size: 0.75em;
  color: var(--text3);
  position: absolute;
  right: -34px;
  white-space: nowrap;
}}

/* ── NICHE BREAKDOWN ────────────────────────────────────── */
.niche-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
  margin-bottom: 32px;
}}
.niche-card {{
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.15s;
}}
.niche-card:hover {{
  border-color: var(--accent);
  background: rgba(136,85,255,0.06);
}}
.nc-top {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}}
.nc-name {{
  font-size: 0.82em;
  font-weight: 700;
  color: #fff;
}}
.nc-gold {{
  font-family: var(--mono);
  font-size: 0.72em;
  color: var(--gold);
  font-weight: 700;
}}
.nc-bar-track {{
  height: 3px;
  background: rgba(255,255,255,0.06);
  border-radius: 2px;
  overflow: hidden;
}}
.nc-bar-fill {{
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--gold));
  border-radius: 2px;
}}
.nc-stats {{
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-family: var(--mono);
  font-size: 0.68em;
  color: var(--text3);
}}

/* ── HIDDEN ─────────────────────────────────────────────── */
.hidden {{ display: none !important; }}

/* ── EMPTY STATE ────────────────────────────────────────── */
.empty-state {{
  text-align: center;
  padding: 60px 20px;
  color: var(--text3);
  font-family: var(--mono);
  font-size: 0.85em;
}}

/* ── PAGE SECTIONS ──────────────────────────────────────── */
.page {{ display: none; }}
.page.active {{ display: block; }}

/* ── ANIMATIONS ─────────────────────────────────────────── */
@keyframes fadeIn {{
  from {{ opacity:0; transform:translateY(10px); }}
  to   {{ opacity:1; transform:translateY(0); }}
}}
.stat-card, .spotlight-card, .niche-card {{
  animation: fadeIn 0.4s ease both;
}}
</style>
</head>
<body>

<!-- SIDEBAR -->
<aside class="sidebar">
  <div class="sidebar-logo">
    <div class="logo-text">THE <em>GIANT</em></div>
    <div class="logo-sub">Intelligence System</div>
  </div>
  <nav class="sidebar-nav">
    <div class="nav-section">Navigation</div>
    <button class="nav-btn active" onclick="showPage('overview',this)">
      <span class="ni">📊</span> Overview
    </button>
    <button class="nav-btn" onclick="showPage('channels',this)">
      <span class="ni">🎯</span> Channel Database
    </button>
    <button class="nav-btn" onclick="showPage('niches',this)">
      <span class="ni">🗂️</span> Niche Breakdown
    </button>

    <div class="nav-section" style="margin-top:20px">Filter by Status</div>
    <button class="nav-btn" onclick="quickFilter('all')">
      <span class="ni">⬜</span> All Channels
    </button>
    <button class="nav-btn" onclick="quickFilter('golden')">
      <span class="ni">⭐</span> Golden Only
    </button>
    <button class="nav-btn" onclick="quickFilter('promising')">
      <span class="ni">▲</span> Promising
    </button>
  </nav>
  <div class="sidebar-footer">
    <div><span class="status-dot"></span>DATABASE ONLINE</div>
    <div>Updated {now}</div>
    <div>intelligence.db</div>
  </div>
</aside>

<!-- MAIN -->
<div class="main">

  <!-- TOP BAR -->
  <div class="topbar">
    <div class="topbar-title">THE GIANT / <span>Intelligence Database</span></div>
    <div class="topbar-right">
      <div class="search-wrap">
        <span class="search-icon">🔍</span>
        <input type="text" id="searchInput" placeholder="Search channels..." oninput="doSearch()">
      </div>
      <div class="time-badge">{now}</div>
    </div>
  </div>

  <!-- CONTENT -->
  <div class="content">

    <!-- ══ PAGE: OVERVIEW ══════════════════════════════════ -->
    <div class="page active" id="page-overview">

      <!-- Stats -->
      <div class="section-header">
        <span class="section-title">Mission Control</span>
        <span class="section-line"></span>
        <span class="section-count">Live Intelligence Summary</span>
      </div>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon">📡</div>
          <div class="stat-val">{total}</div>
          <div class="stat-label">Total Channels</div>
          <div class="stat-sub">Scanned &amp; Scored</div>
        </div>
        <div class="stat-card gold">
          <div class="stat-icon">⭐</div>
          <div class="stat-val gold">{golden_count}</div>
          <div class="stat-label">Golden Channels</div>
          <div class="stat-sub">{golden_pct}% of total</div>
        </div>
        <div class="stat-card blue">
          <div class="stat-icon">🗂️</div>
          <div class="stat-val blue">{niche_count}</div>
          <div class="stat-label">Niches Covered</div>
          <div class="stat-sub">Active research areas</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">🔑</div>
          <div class="stat-val">{keyword_count}</div>
          <div class="stat-label">Keywords Used</div>
          <div class="stat-sub">Search queries run</div>
        </div>
        <div class="stat-card green">
          <div class="stat-icon">▲</div>
          <div class="stat-val green">{s_prom}</div>
          <div class="stat-label">Promising</div>
          <div class="stat-sub">Score 35–54</div>
        </div>
        <div class="stat-card red">
          <div class="stat-icon">🧩</div>
          <div class="stat-val" style="color:var(--accent2)">{tp_count}</div>
          <div class="stat-label">Title Patterns</div>
          <div class="stat-sub">Extracted formulas</div>
        </div>
      </div>

      <!-- Top Golden Spotlight -->
      {'<div class="section-header"><span class="section-title">Top Golden Channels</span><span class="section-line"></span><span class="section-count">Highest Scoring Discoveries</span></div><div class="spotlight-row">' + spotlight + '</div>' if spotlight else ''}

      <!-- Quick Channel Table (overview) -->
      <div class="section-header">
        <span class="section-title">Recent Discoveries</span>
        <span class="section-line"></span>
        <span class="section-count">All Channels · Sorted by Score</span>
      </div>
      <div class="filter-bar">
        <span class="filter-label">Filter:</span>
        <button class="filter-btn active" id="fb-all" onclick="tableFilter('all',this)">All</button>
        <button class="filter-btn f-gold" id="fb-gold" onclick="tableFilter('golden',this)">⭐ Golden</button>
        <button class="filter-btn f-prom" id="fb-prom" onclick="tableFilter('promising',this)">▲ Promising</button>
        <span class="filter-label" style="margin-left:8px">Niche:</span>
        {niche_btns}
      </div>
      <div class="table-wrap">
        <div class="table-toolbar">
          <div class="table-toolbar-left">Showing <span id="rowCount">{len(channels)}</span> channels</div>
          <div class="sort-btns">
            <button class="sort-btn active" onclick="sortTable('score')">Score ↓</button>
            <button class="sort-btn" onclick="sortTable('subs')">Subs ↓</button>
            <button class="sort-btn" onclick="sortTable('age')">Newest</button>
            <button class="sort-btn" onclick="sortTable('vpv')">VPV ↓</button>
          </div>
        </div>
        <div class="tbl-outer">
          <table id="mainTable">
            <thead>
              <tr>
                <th onclick="sortTable('score')">Status</th>
                <th onclick="sortTable('name')">Channel</th>
                <th onclick="sortTable('score')">Score ↕</th>
                <th onclick="sortTable('age')">Age ↕</th>
                <th>Last Video</th>
                <th onclick="sortTable('subs')">Subscribers ↕</th>
                <th>Videos</th>
                <th onclick="sortTable('vpv')">VPV ↕</th>
                <th>Faceless</th>
                <th>Niche</th>
                <th>Found Via</th>
              </tr>
            </thead>
            <tbody id="tableBody">
              {rows}
            </tbody>
          </table>
        </div>
      </div>

    </div><!-- /overview -->

    <!-- ══ PAGE: CHANNELS ══════════════════════════════════ -->
    <div class="page" id="page-channels">
      <div class="section-header">
        <span class="section-title">Channel Database</span>
        <span class="section-line"></span>
        <span class="section-count">Full Intelligence Records</span>
      </div>
      <div class="filter-bar">
        <span class="filter-label">Status:</span>
        <button class="filter-btn active" onclick="tableFilter('all',this)">All</button>
        <button class="filter-btn f-gold" onclick="tableFilter('golden',this)">⭐ Golden Only</button>
        <button class="filter-btn f-prom" onclick="tableFilter('promising',this)">▲ Promising</button>
      </div>
      <div class="table-wrap">
        <div class="table-toolbar">
          <div class="table-toolbar-left">Showing <span id="rowCount2">{len(channels)}</span> channels</div>
        </div>
        <div class="tbl-outer">
          <table>
            <thead><tr>
              <th>Status</th><th>Channel</th><th>Score</th>
              <th>Age</th><th>Last Video</th><th>Subscribers</th>
              <th>Videos</th><th>VPV</th><th>Faceless</th>
              <th>Niche</th><th>Found Via</th>
            </tr></thead>
            <tbody id="tableBody2">{rows}</tbody>
          </table>
        </div>
      </div>
    </div><!-- /channels -->

    <!-- ══ PAGE: NICHES ════════════════════════════════════ -->
    <div class="page" id="page-niches">
      <div class="section-header">
        <span class="section-title">Niche Breakdown</span>
        <span class="section-line"></span>
        <span class="section-count">{niche_count} Niches Researched</span>
      </div>
      <div class="niche-grid" id="nicheGrid">
        <!-- Populated by JS -->
      </div>
    </div><!-- /niches -->

  </div><!-- /content -->
</div><!-- /main -->

<script>
// ── DATA ────────────────────────────────────────────────
var NICHES = {{json_niches}};

// ── PAGE NAVIGATION ──────────────────────────────────────
function showPage(id, btn) {{
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + id).classList.add('active');
  if (btn) btn.classList.add('active');
  if (id === 'niches') renderNiches();
}}

function quickFilter(type) {{
  showPage('overview', null);
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  if (type === 'all') tableFilter('all', document.getElementById('fb-all'));
  if (type === 'golden') tableFilter('golden', document.getElementById('fb-gold'));
  if (type === 'promising') tableFilter('promising', document.getElementById('fb-prom'));
}}

// ── TABLE FILTER ─────────────────────────────────────────
var activeFilter = 'all';
var activeNiche  = null;

function tableFilter(type, btn) {{
  activeFilter = type;
  activeNiche  = null;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.niche-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  applyFilters();
}}

function filterNiche(btn) {{
  activeNiche  = btn.dataset.niche;
  activeFilter = 'all';
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.niche-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}}

function applyFilters() {{
  var q    = (document.getElementById('searchInput').value || '').toLowerCase();
  var rows = document.querySelectorAll('#tableBody tr');
  var vis  = 0;
  rows.forEach(function(r) {{
    var show = true;
    if (activeFilter === 'golden'   && r.dataset.golden !== '1') show = false;
    if (activeFilter === 'promising'&& !r.classList.contains('row-prom')) show = false;
    if (activeNiche && r.dataset.niche !== activeNiche) show = false;
    if (q) {{
      var name = r.cells[1] ? r.cells[1].innerText.toLowerCase() : '';
      if (!name.includes(q)) show = false;
    }}
    r.style.display = show ? '' : 'none';
    if (show) vis++;
  }});
  var rc = document.getElementById('rowCount');
  if (rc) rc.textContent = vis;
}}

function doSearch() {{ applyFilters(); }}

// ── SORT ─────────────────────────────────────────────────
function sortTable(col) {{
  document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
  event && event.target && event.target.classList && event.target.classList.add('active');

  var tbody = document.getElementById('tableBody');
  var rows  = Array.from(tbody.querySelectorAll('tr'));

  rows.sort(function(a, b) {{
    if (col === 'score') {{
      return parseInt(b.dataset.score||0) - parseInt(a.dataset.score||0);
    }}
    if (col === 'subs') {{
      var as = a.cells[5] ? a.cells[5].innerText.replace(/,/g,'') : '0';
      var bs = b.cells[5] ? b.cells[5].innerText.replace(/,/g,'') : '0';
      return parseInt(bs) - parseInt(as);
    }}
    if (col === 'age') {{
      var av = a.cells[3] ? parseInt(a.cells[3].innerText) || 9999 : 9999;
      var bv = b.cells[3] ? parseInt(b.cells[3].innerText) || 9999 : 9999;
      return av - bv;
    }}
    if (col === 'vpv') {{
      var av2 = a.cells[7] ? parseVpv(a.cells[7].innerText) : 0;
      var bv2 = b.cells[7] ? parseVpv(b.cells[7].innerText) : 0;
      return bv2 - av2;
    }}
    if (col === 'name') {{
      var an = a.cells[1] ? a.cells[1].innerText.toLowerCase() : '';
      var bn = b.cells[1] ? b.cells[1].innerText.toLowerCase() : '';
      return an.localeCompare(bn);
    }}
    return 0;
  }});
  rows.forEach(function(r) {{ tbody.appendChild(r); }});
}}

function parseVpv(s) {{
  s = s.trim();
  if (s.endsWith('M')) return parseFloat(s) * 1000000;
  if (s.endsWith('K')) return parseFloat(s) * 1000;
  return parseInt(s) || 0;
}}

// ── NICHE GRID ───────────────────────────────────────────
function renderNiches() {{
  var grid = document.getElementById('nicheGrid');
  if (!grid || !NICHES.length) return;
  var maxTotal = Math.max.apply(null, NICHES.map(function(n){{return n.total||1;}}));
  grid.innerHTML = NICHES.map(function(n) {{
    var pct = Math.round(((n.golden||0) / Math.max(n.total,1)) * 100);
    var barW = Math.round(((n.total||0) / maxTotal) * 100);
    return '<div class="niche-card" onclick="filterNicheByName(\\'' + n.niche.replace(/'/g,"\\'") + '\\')">' +
      '<div class="nc-top"><span class="nc-name">' + n.niche + '</span>' +
      '<span class="nc-gold">⭐ ' + (n.golden||0) + '</span></div>' +
      '<div class="nc-bar-track"><div class="nc-bar-fill" style="width:' + barW + '%"></div></div>' +
      '<div class="nc-stats"><span>' + n.total + ' channels</span><span>' + pct + '% golden</span></div>' +
      '</div>';
  }}).join('');
}}

function filterNicheByName(name) {{
  showPage('overview', document.querySelector('.nav-btn'));
  document.querySelectorAll('.nav-btn')[1].classList.add('active');
  activeNiche  = name;
  activeFilter = 'all';
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.niche-btn').forEach(function(b) {{
    if (b.dataset.niche === name) b.classList.add('active');
    else b.classList.remove('active');
  }});
  applyFilters();
}}
</script>
</body>
</html>"""


def main():
    print("=" * 55)
    print("  THE GIANT — Generating Professional Dashboard")
    print("=" * 55)

    data = load_data()

    channels, total, golden_count, niche_count, keyword_count, niches, \
        top_golden, s_gold, s_prom, s_reg, tp_count = data

    import json as _json
    json_niches = _json.dumps(niches)

    html = generate_html(
        channels, total, golden_count, niche_count, keyword_count,
        niches, top_golden, s_gold, s_prom, s_reg, tp_count
    )

    # Inject niche data for JS
    html = html.replace("{json_niches}", json_niches)

    with open("viewer.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n  Dashboard ready.")
    print(f"  Total channels  : {total}")
    print(f"  Golden channels : {golden_count}")
    print(f"  Niches          : {niche_count}")
    print(f"\n  Double-click viewer.html to open in browser.")


if __name__ == "__main__":
    main()
