import yt_dlp
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from config import (DB_FILE, RESULTS_PER_KEYWORD,
                    GOLDEN_SCORE_MIN, MAX_SUBSCRIBERS, MIN_SUBSCRIBERS)

MAX_CHANNEL_AGE_DAYS  = 180
MAX_LAST_VIDEO_DAYS   = 40


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keywords (
        keyword          TEXT PRIMARY KEY,
        subtopic         TEXT,
        priority         INTEGER DEFAULT 5,
        searched         INTEGER DEFAULT 0,
        date_added       TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS channels (
        channel_id       TEXT PRIMARY KEY,
        channel_name     TEXT,
        channel_url      TEXT,
        subscribers      INTEGER,
        total_views      INTEGER,
        video_count      INTEGER,
        discovered_via   TEXT,
        golden_score     INTEGER,
        is_golden        INTEGER DEFAULT 0,
        channel_age_days INTEGER,
        last_video_days  INTEGER,
        date_found       TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS videos (
        video_id         TEXT PRIMARY KEY,
        channel_id       TEXT,
        title            TEXT,
        views            INTEGER,
        upload_date      TEXT,
        duration         INTEGER,
        url              TEXT,
        video_score      REAL DEFAULT 0
    )''')
    conn.commit()
    return conn


def load_keywords(conn):
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM keywords")
    count = c.fetchone()[0]
    if count == 0:
        print("No keywords in database. Run keyword_generator.py first.")
        print("Using 12 seed keywords for now.\n")
        return [
            ("ancient mysteries explained",    "Ancient Mysteries"),
            ("dark history facts",             "Dark History"),
            ("hidden secrets of history",      "Forbidden Knowledge"),
            ("unsolved mysteries documentary", "Unsolved Crimes"),
            ("forbidden history secrets",      "Forbidden Knowledge"),
            ("lost civilizations explained",   "Lost Civilizations"),
            ("dark secrets of ancient world",  "Ancient Mysteries"),
            ("secret societies exposed",       "Secret Societies"),
            ("ancient weapons explained",      "Ancient Weapons"),
            ("empire collapse explained",      "Empire Collapses"),
            ("historical betrayal explained",  "Historical Betrayals"),
            ("mythology explained simply",     "Mythology Explained"),
        ]
    c.execute("SELECT keyword, subtopic FROM keywords WHERE searched = 0")
    rows = c.fetchall()
    if not rows:
        print("All keywords already searched. Resetting for fresh run...")
        c.execute("UPDATE keywords SET searched = 0")
        conn.commit()
        c.execute("SELECT keyword, subtopic FROM keywords WHERE searched = 0")
        rows = c.fetchall()
    return rows


def mark_keyword_searched(conn, keyword):
    c = conn.cursor()
    c.execute("UPDATE keywords SET searched = 1 WHERE keyword = ?", (keyword,))
    conn.commit()


def get_channel_video_dates(channel_url):
    ydl_opts = {
        "quiet":        True,
        "no_warnings":  True,
        "extract_flat": True,
        "playlistend":  200,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
        entries = info.get("entries") or []
        dates = []
        for e in entries:
            if not e:
                continue
            raw = e.get("upload_date")
            if raw and len(raw) == 8:
                try:
                    dates.append(
                        datetime.strptime(raw, "%Y%m%d").replace(tzinfo=timezone.utc)
                    )
                except ValueError:
                    pass
        if dates:
            return min(dates), max(dates)
    except Exception:
        pass
    return None, None


def calculate_golden_score(info, subscribers, age_days=None, last_video_days=None):
    score = 0
    subs       = subscribers
    vid_count  = info.get("playlist_count") or 0
    view_count = info.get("view_count") or 0

    if 5000 <= subs <= 100000:
        score += 25
    elif 100000 < subs <= 300000:
        score += 15
    elif 300000 < subs <= 500000:
        score += 5

    if 8 <= vid_count <= 80:
        score += 15

    if subs > 0:
        ratio = view_count / max(subs, 1)
        if ratio > 20:
            score += 20
        elif ratio > 10:
            score += 12
        elif ratio > 5:
            score += 7

    strong_keywords = [
        "history", "mystery", "mysteries", "ancient", "secret",
        "hidden", "unknown", "facts", "dark", "forbidden",
        "explained", "civilization", "archaeology", "myth",
        "conspiracy", "unsolved", "lost", "empire", "betrayal"
    ]
    name = (info.get("channel") or "").lower()
    desc = (info.get("description") or "").lower()
    matches = sum(1 for k in strong_keywords if k in name or k in desc)
    score += min(matches * 5, 20)

    if vid_count >= 5:
        score += 10

    if age_days is not None:
        if age_days <= 30:
            score += 20
        elif age_days <= 60:
            score += 15
        elif age_days <= 90:
            score += 10
        elif age_days <= 120:
            score += 7
        elif age_days <= 150:
            score += 4
        else:
            score += 2

    if last_video_days is not None:
        if last_video_days <= 7:
            score += 10
        elif last_video_days <= 14:
            score += 7
        elif last_video_days <= 30:
            score += 4

    return min(score, 100)


def search_keyword(keyword, max_results=20):
    found = {}
    ydl_opts = {
        "quiet":          True,
        "no_warnings":    True,
        "extract_flat":   True,
        "playlist_items": f"1-{max_results}",
    }
    url = f"ytsearch{max_results}:{keyword}"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=False)
        entries = result.get("entries") or []
        for entry in entries:
            if not entry:
                continue
            cid  = entry.get("channel_id")
            curl = entry.get("channel_url")
            if not cid or not curl:
                continue
            if cid not in found:
                found[cid] = {
                    "channel_id":     cid,
                    "channel_name":   entry.get("channel", "Unknown"),
                    "channel_url":    curl,
                    "discovered_via": keyword,
                }
    except Exception as e:
        print(f"  Search error: {e}")
    return found


def score_channel(channel):
    ydl_opts = {
        "quiet":        True,
        "no_warnings":  True,
        "extract_flat": True,
        "playlistend":  1,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel["channel_url"], download=False)

        subs = info.get("channel_follower_count") or 0

        if subs > MAX_SUBSCRIBERS or (subs > 0 and subs < MIN_SUBSCRIBERS):
            return None

        now = datetime.now(timezone.utc)
        first_date, last_date = get_channel_video_dates(channel["channel_url"])

        age_days        = None
        last_video_days = None

        if first_date is not None:
            cutoff = now - timedelta(days=MAX_CHANNEL_AGE_DAYS)
            if first_date < cutoff:
                days = (now - first_date).days
                print(f"  SKIP old channel ({days}d): {channel['channel_name']}")
                return None
            age_days = (now - first_date).days

        if last_date is not None:
            last_video_days = (now - last_date).days
            if last_video_days > MAX_LAST_VIDEO_DAYS:
                print(f"  SKIP inactive ({last_video_days}d no upload): {channel['channel_name']}")
                return None

        age_str  = f"{age_days}d"        if age_days        is not None else "?d"
        last_str = f"{last_video_days}d" if last_video_days is not None else "?d"
        print(f"  OK age:{age_str} last:{last_str} — {channel['channel_name']}")

        channel["subscribers"]      = subs
        channel["total_views"]      = info.get("view_count") or 0
        channel["video_count"]      = info.get("playlist_count") or 0
        channel["channel_age_days"] = age_days
        channel["last_video_days"]  = last_video_days
        channel["golden_score"]     = calculate_golden_score(
            info, subs, age_days, last_video_days
        )
        channel["is_golden"] = 1 if channel["golden_score"] >= GOLDEN_SCORE_MIN else 0

    except Exception as e:
        channel["subscribers"]      = 0
        channel["total_views"]      = 0
        channel["video_count"]      = 0
        channel["channel_age_days"] = None
        channel["last_video_days"]  = None
        channel["golden_score"]     = 0
        channel["is_golden"]        = 0

    channel["date_found"] = datetime.now(timezone.utc).isoformat()
    return channel


def channel_exists(conn, channel_id):
    c = conn.cursor()
    c.execute("SELECT 1 FROM channels WHERE channel_id = ?", (channel_id,))
    return c.fetchone() is not None


def save_channel(conn, channel):
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO channels VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?)''', (
        channel["channel_id"],
        channel["channel_name"],
        channel["channel_url"],
        channel["subscribers"],
        channel["total_views"],
        channel["video_count"],
        channel["discovered_via"],
        channel["golden_score"],
        channel["is_golden"],
        channel.get("channel_age_days"),
        channel.get("last_video_days"),
        channel["date_found"],
    ))
    conn.commit()


def print_channel_status(channel):
    score     = channel["golden_score"]
    subs      = channel["subscribers"]
    name      = channel["channel_name"]
    age       = channel.get("channel_age_days")
    last      = channel.get("last_video_days")
    age_str   = f"{age}d"  if age  is not None else "?d"
    last_str  = f"{last}d" if last is not None else "?d"

    if score >= GOLDEN_SCORE_MIN:
        tag = "*** GOLDEN ***"
    elif score >= 35:
        tag = ">> PROMISING  "
    else:
        tag = "   regular    "

    print(f"  {tag} | Score:{score:>3} | Age:{age_str:>5} "
          f"| Last:{last_str:>5} | Subs:{subs:>8,} | {name}")


def main():
    print("=" * 70)
    print("  THE GIANT — Channel Discovery Engine")
    print("  Filters: 6-month age  +  1-month activity  +  subscriber range")
    print("=" * 70)

    conn     = init_db()
    keywords = load_keywords(conn)
    total_kw = len(keywords)

    print(f"\n  Keywords loaded      : {total_kw}")
    print(f"  Results per keyword  : {RESULTS_PER_KEYWORD}")
    print(f"  Max channel age      : {MAX_CHANNEL_AGE_DAYS} days")
    print(f"  Max last video age   : {MAX_LAST_VIDEO_DAYS} days")
    print(f"  Golden threshold     : {GOLDEN_SCORE_MIN}/100")
    print(f"\n  Starting...\n")
    print("-" * 70)

    all_found   = {}
    golden_list = []

    for idx, (keyword, subtopic) in enumerate(keywords, 1):
        print(f"\n[{idx}/{total_kw}] {keyword} ({subtopic})")

        found = search_keyword(keyword, max_results=RESULTS_PER_KEYWORD)
        new_channels = {
            cid: ch for cid, ch in found.items()
            if cid not in all_found and not channel_exists(conn, cid)
        }
        all_found.update(found)
        print(f"  {len(found)} channels found | {len(new_channels)} new to score")

        for cid, ch in new_channels.items():
            scored = score_channel(ch)
            if scored is None:
                continue
            save_channel(conn, scored)
            print_channel_status(scored)
            if scored["is_golden"]:
                golden_list.append(scored)

        mark_keyword_searched(conn, keyword)
        time.sleep(0.5)

    print(f"\n{'='*70}")
    print(f"  DISCOVERY COMPLETE")
    print(f"{'='*70}")
    print(f"  Keywords searched    : {total_kw}")
    print(f"  Total channels found : {len(all_found)}")
    print(f"  Golden channels      : {len(golden_list)}")

    if golden_list:
        print(f"\n  YOUR GOLDEN CHANNELS")
        print(f"  {'='*65}")
        for g in sorted(golden_list, key=lambda x: x["golden_score"], reverse=True):
            print(f"\n  Channel  : {g['channel_name']}")
            print(f"  Score    : {g['golden_score']}/100")
            print(f"  Age      : {g.get('channel_age_days')} days old")
            print(f"  Last vid : {g.get('last_video_days')} days ago")
            print(f"  Subs     : {g['subscribers']:,}")
            print(f"  Videos   : {g['video_count']}")
            print(f"  Found via: {g['discovered_via']}")
            print(f"  URL      : {g['channel_url']}")

    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM channels WHERE is_golden = 1")
    total_golden_db = c.fetchone()[0]
    print(f"\n  Total golden in database : {total_golden_db}")
    print(f"  Data saved to           : {DB_FILE}")
    print(f"\n  Open viewer.html in your browser to see full results.")
    conn.close()


if __name__ == "__main__":
    main()
