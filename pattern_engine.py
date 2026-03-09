import sqlite3
import requests
import yt_dlp
import json
import time
from datetime import datetime, timezone
from config import GROQ_API_KEY, DB_FILE, GROQ_MODEL


# ================================================================
#  DATABASE SETUP
# ================================================================
def init_pattern_tables(conn):
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS channel_titles (
        video_id      TEXT PRIMARY KEY,
        channel_id    TEXT,
        channel_name  TEXT,
        niche         TEXT,
        title         TEXT,
        views         INTEGER,
        upload_date   TEXT,
        thumbnail_url TEXT,
        video_url     TEXT,
        fetched_at    TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS title_patterns (
        pattern_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        niche           TEXT,
        pattern_formula TEXT,
        example_title   TEXT,
        emotion_trigger TEXT,
        curiosity_style TEXT,
        format_type     TEXT,
        power_words     TEXT,
        ctr_score       INTEGER,
        times_seen      INTEGER DEFAULT 1,
        date_found      TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS thumbnail_patterns (
        pattern_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        niche            TEXT,
        visual_style     TEXT,
        composition_type TEXT,
        color_scheme     TEXT,
        text_on_thumb    TEXT,
        symbol_used      TEXT,
        emotion_conveyed TEXT,
        example_channel  TEXT,
        ctr_score        INTEGER,
        times_seen       INTEGER DEFAULT 1,
        date_found       TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS niche_intelligence (
        niche              TEXT PRIMARY KEY,
        top_title_formulas TEXT,
        top_emotions       TEXT,
        top_power_words    TEXT,
        top_thumb_styles   TEXT,
        top_topics         TEXT,
        avoid_patterns     TEXT,
        last_updated       TEXT
    )''')

    conn.commit()


# ================================================================
#  FETCH TITLES FROM A CHANNEL
# ================================================================
def fetch_channel_titles(channel_id, channel_url, channel_name, niche, max_videos=30):
    ydl_opts = {
        "quiet":        True,
        "no_warnings":  True,
        "extract_flat": True,
        "playlistend":  max_videos,
    }
    titles = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)

        entries = info.get("entries") or []
        for e in entries:
            if not e:
                continue
            vid_id = e.get("id") or e.get("video_id")
            title  = e.get("title")
            if not vid_id or not title:
                continue
            thumb = f"https://img.youtube.com/vi/{vid_id}/maxresdefault.jpg"
            titles.append({
                "video_id":      vid_id,
                "channel_id":    channel_id,
                "channel_name":  channel_name,
                "niche":         niche,
                "title":         title,
                "views":         e.get("view_count") or 0,
                "upload_date":   e.get("upload_date") or "",
                "thumbnail_url": thumb,
                "video_url":     f"https://www.youtube.com/watch?v={vid_id}",
                "fetched_at":    datetime.now(timezone.utc).isoformat(),
            })
    except Exception as e:
        print(f"    Error fetching titles: {e}")
    return titles


def save_titles(conn, titles):
    c = conn.cursor()
    saved = 0
    for t in titles:
        try:
            c.execute('''INSERT OR IGNORE INTO channel_titles VALUES
                (?,?,?,?,?,?,?,?,?,?)''', (
                t["video_id"],
                t["channel_id"],
                t["channel_name"],
                t["niche"],
                t["title"],
                t["views"],
                t["upload_date"],
                t["thumbnail_url"],
                t["video_url"],
                t["fetched_at"],
            ))
            saved += 1
        except Exception:
            pass
    conn.commit()
    return saved


# ================================================================
#  GROQ AI ANALYSIS
# ================================================================
def call_groq(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json"
    }
    payload = {
        "model":       GROQ_MODEL,
        "messages":    [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens":  4000
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def analyze_title_patterns(titles_list, niche):
    titles_text = "\n".join([f"- {t}" for t in titles_list[:60]])

    prompt = f"""You are an expert YouTube title analyst for faceless channels.

Niche: {niche}

Here are real titles from fast-growing faceless channels in this niche:
{titles_text}

Analyze these titles deeply and extract the exact repeating patterns.

Return ONLY valid JSON in this exact format:

{{
  "title_formulas": [
    {{
      "formula": "The [TIMEFRAME] [TOPIC] That [SHOCKING OUTCOME]",
      "example": "The 10-Minute Habit That Rewires Your Brain",
      "emotion_trigger": "curiosity + transformation",
      "curiosity_style": "mechanism reveal",
      "format_type": "transformation formula",
      "power_words": ["rewires", "habit", "10-minute"],
      "ctr_score": 85
    }}
  ],
  "thumbnail_patterns": [
    {{
      "visual_style": "dark background with glowing subject",
      "composition_type": "single dominant object center",
      "color_scheme": "dark red and black",
      "text_on_thumb": "large bold white text top",
      "symbol_used": "skull or ancient artifact",
      "emotion_conveyed": "fear and curiosity",
      "ctr_score": 80
    }}
  ],
  "top_emotions": ["curiosity", "fear", "shock", "mystery"],
  "top_power_words": ["hidden", "secret", "dark", "forbidden", "lost"],
  "top_topics": ["topic1", "topic2", "topic3", "topic4", "topic5"],
  "avoid_patterns": ["boring academic titles", "too long titles", "no emotional trigger"],
  "niche_intelligence": "Key insight about what makes this niche work on YouTube"
}}

Extract at least 8 title formulas and 5 thumbnail patterns.
Be very specific and practical."""

    raw = call_groq(prompt)
    raw = raw.strip()
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    raw   = raw[start:end]
    return json.loads(raw)


# ================================================================
#  SAVE PATTERNS TO DATABASE
# ================================================================
def save_patterns(conn, niche, analysis, channel_name):
    c   = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    # Save title patterns
    for p in analysis.get("title_formulas", []):
        c.execute('''INSERT INTO title_patterns
            (niche, pattern_formula, example_title, emotion_trigger,
             curiosity_style, format_type, power_words, ctr_score, date_found)
            VALUES (?,?,?,?,?,?,?,?,?)''', (
            niche,
            p.get("formula", ""),
            p.get("example", ""),
            p.get("emotion_trigger", ""),
            p.get("curiosity_style", ""),
            p.get("format_type", ""),
            json.dumps(p.get("power_words", [])),
            p.get("ctr_score", 50),
            now,
        ))

    # Save thumbnail patterns
    for p in analysis.get("thumbnail_patterns", []):
        c.execute('''INSERT INTO thumbnail_patterns
            (niche, visual_style, composition_type, color_scheme,
             text_on_thumb, symbol_used, emotion_conveyed,
             example_channel, ctr_score, date_found)
            VALUES (?,?,?,?,?,?,?,?,?,?)''', (
            niche,
            p.get("visual_style", ""),
            p.get("composition_type", ""),
            p.get("color_scheme", ""),
            p.get("text_on_thumb", ""),
            p.get("symbol_used", ""),
            p.get("emotion_conveyed", ""),
            channel_name,
            p.get("ctr_score", 50),
            now,
        ))

    # Save niche intelligence summary
    c.execute('''INSERT OR REPLACE INTO niche_intelligence VALUES
        (?,?,?,?,?,?,?,?)''', (
        niche,
        json.dumps(analysis.get("title_formulas", [])[:5]),
        json.dumps(analysis.get("top_emotions", [])),
        json.dumps(analysis.get("top_power_words", [])),
        json.dumps(analysis.get("thumbnail_patterns", [])[:5]),
        json.dumps(analysis.get("top_topics", [])),
        json.dumps(analysis.get("avoid_patterns", [])),
        now,
    ))

    conn.commit()


# ================================================================
#  PRINT PATTERN REPORT
# ================================================================
def print_pattern_report(niche, analysis):
    print(f"\n  {'='*60}")
    print(f"  PATTERN INTELLIGENCE — {niche.upper()}")
    print(f"  {'='*60}")

    print(f"\n  TOP TITLE FORMULAS:")
    for i, p in enumerate(analysis.get("title_formulas", [])[:5], 1):
        print(f"\n  {i}. Formula : {p.get('formula', '')}")
        print(f"     Example : {p.get('example', '')}")
        print(f"     Emotion : {p.get('emotion_trigger', '')}")
        print(f"     CTR     : {p.get('ctr_score', 0)}/100")

    print(f"\n  TOP THUMBNAIL PATTERNS:")
    for i, p in enumerate(analysis.get("thumbnail_patterns", [])[:4], 1):
        print(f"\n  {i}. Style      : {p.get('visual_style', '')}")
        print(f"     Colors     : {p.get('color_scheme', '')}")
        print(f"     Symbol     : {p.get('symbol_used', '')}")
        print(f"     Emotion    : {p.get('emotion_conveyed', '')}")
        print(f"     CTR        : {p.get('ctr_score', 0)}/100")

    print(f"\n  TOP POWER WORDS : {', '.join(analysis.get('top_power_words', []))}")
    print(f"  TOP EMOTIONS    : {', '.join(analysis.get('top_emotions', []))}")
    print(f"  TOP TOPICS      : {', '.join(analysis.get('top_topics', [])[:5])}")
    print(f"\n  AVOID            : {', '.join(analysis.get('avoid_patterns', []))}")
    print(f"\n  INSIGHT: {analysis.get('niche_intelligence', '')}")


# ================================================================
#  MAIN
# ================================================================
def main():
    print("=" * 65)
    print("  THE GIANT — Pattern Intelligence Engine")
    print("  Extracts title and thumbnail formulas from")
    print("  golden and promising channels")
    print("=" * 65)

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    init_pattern_tables(conn)

    # Ask which niche to analyze
    print()
    c = conn.cursor()
    c.execute("SELECT DISTINCT niche FROM channels ORDER BY niche")
    available = [row[0] for row in c.fetchall()]

    if not available:
        print("  No channels in database yet.")
        print("  Run giant.py first to discover channels.")
        conn.close()
        return

    print("  Available niches in your database:")
    for i, n in enumerate(available, 1):
        print(f"    [{i}] {n}")
    print(f"    [A] All niches together")
    print()

    choice = input("  Choose niche number or A: ").strip().lower()

    if choice == "a":
        target_niches = available
    else:
        try:
            idx = int(choice) - 1
            target_niches = [available[idx]]
        except (ValueError, IndexError):
            print("  Invalid choice.")
            conn.close()
            return

    for niche in target_niches:
        print(f"\n{'='*65}")
        print(f"  Processing niche: {niche.upper()}")
        print(f"{'='*65}")

        # Load golden and promising channels for this niche
        c.execute('''SELECT channel_id, channel_url, channel_name
                     FROM channels
                     WHERE niche=? AND (is_golden=1 OR golden_score >= 35)
                     ORDER BY golden_score DESC''', (niche,))
        channels = c.fetchall()

        if not channels:
            print(f"  No golden or promising channels found for {niche}")
            print(f"  Run giant.py first.")
            continue

        print(f"  Found {len(channels)} channels to analyze")

        all_titles   = []
        channel_info = []

        for ch in channels:
            cid   = ch["channel_id"]
            curl  = ch["channel_url"]
            cname = ch["channel_name"]

            print(f"\n  Fetching titles from: {cname}")
            titles = fetch_channel_titles(cid, curl, cname, niche, max_videos=30)

            if titles:
                saved = save_titles(conn, titles)
                print(f"    {len(titles)} videos fetched, {saved} new saved")
                all_titles.extend([t["title"] for t in titles])
                channel_info.append(cname)
            else:
                print(f"    No titles found")

            time.sleep(0.5)

        if len(all_titles) < 5:
            print(f"\n  Not enough titles to analyze ({len(all_titles)} found)")
            print(f"  Need at least 5 titles. Skipping pattern analysis.")
            continue

        # Remove duplicates
        all_titles = list(set(all_titles))
        print(f"\n  Total unique titles collected: {len(all_titles)}")
        print(f"  Sending to Groq AI for pattern analysis...")

        try:
            analysis = analyze_title_patterns(all_titles, niche)
            save_patterns(conn, niche, analysis, ", ".join(channel_info[:3]))
            print_pattern_report(niche, analysis)
            print(f"\n  Patterns saved to database.")
        except json.JSONDecodeError:
            print("  AI returned bad format. Try running again.")
        except requests.HTTPError as e:
            print(f"  Groq API error: {e}")

    # Final summary
    c.execute("SELECT COUNT(*) FROM title_patterns")
    tp = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM thumbnail_patterns")
    thp = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM channel_titles")
    ct = c.fetchone()[0]

    print(f"\n{'='*65}")
    print(f"  PATTERN ENGINE COMPLETE")
    print(f"{'='*65}")
    print(f"  Total titles collected    : {ct}")
    print(f"  Title patterns extracted  : {tp}")
    print(f"  Thumbnail patterns stored : {thp}")
    print(f"\n  Run viewer.py to see full dashboard with patterns.")

    conn.close()


if __name__ == "__main__":
    main()
