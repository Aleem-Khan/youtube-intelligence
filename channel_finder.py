import yt_dlp
import sqlite3
import json
from datetime import datetime, timezone

def init_db():
    conn = sqlite3.connect("intelligence.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS channels (
        channel_id      TEXT PRIMARY KEY,
        channel_name    TEXT,
        channel_url     TEXT,
        subscribers     INTEGER,
        total_views     INTEGER,
        video_count     INTEGER,
        discovered_via  TEXT,
        golden_score    INTEGER,
        date_found      TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS videos (
        video_id        TEXT PRIMARY KEY,
        channel_id      TEXT,
        title           TEXT,
        views           INTEGER,
        upload_date     TEXT,
        duration        INTEGER,
        url             TEXT
    )''')
    conn.commit()
    return conn

def calculate_golden_score(info):
    score = 0
    subs       = info.get("channel_follower_count") or 0
    view_count = info.get("view_count") or 0
    vid_count  = info.get("playlist_count") or 0

    if 10000 <= subs <= 200000:
        score += 20

    if 10 <= vid_count <= 60:
        score += 15

    if subs > 0 and (view_count / max(subs, 1)) > 5:
        score += 20

    keywords = ["history", "mystery", "mysteries", "ancient",
                "secret", "hidden", "unknown", "facts",
                "dark", "world", "explained", "universe"]
    name = (info.get("channel") or "").lower()
    desc = (info.get("description") or "").lower()
    if any(k in name or k in desc for k in keywords):
        score += 25

    if vid_count > 0:
        score += 10

    return min(score, 100)

def search_channels(keywords, max_per_keyword=5):
    found = {}

    ydl_opts = {
        "quiet":          True,
        "no_warnings":    True,
        "extract_flat":   True,
        "playlist_items": f"1-{max_per_keyword}",
    }

    for keyword in keywords:
        print(f"\n Searching: {keyword}")
        url = f"ytsearch{max_per_keyword}:{keyword}"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(url, download=False)

            entries = result.get("entries") or []
            for entry in entries:
                if not entry:
                    continue
                cid  = entry.get("channel_id")
                curl = entry.get("channel_url")
                if not cid or not curl or cid in found:
                    continue
                found[cid] = {
                    "channel_id":    cid,
                    "channel_name":  entry.get("channel", "Unknown"),
                    "channel_url":   curl,
                    "discovered_via": keyword,
                }
        except Exception as e:
            print(f"  Error on '{keyword}': {e}")

    return list(found.values())

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

        channel["subscribers"]  = info.get("channel_follower_count") or 0
        channel["total_views"]  = info.get("view_count") or 0
        channel["video_count"]  = info.get("playlist_count") or 0
        channel["golden_score"] = calculate_golden_score(info)
    except Exception as e:
        print(f"  Could not score {channel['channel_name']}: {e}")
        channel["subscribers"]  = 0
        channel["total_views"]  = 0
        channel["video_count"]  = 0
        channel["golden_score"] = 0

    channel["date_found"] = datetime.now(timezone.utc).isoformat()
    return channel

def save_channel(conn, channel):
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO channels VALUES (?,?,?,?,?,?,?,?,?)''', (
        channel["channel_id"],
        channel["channel_name"],
        channel["channel_url"],
        channel["subscribers"],
        channel["total_views"],
        channel["video_count"],
        channel["discovered_via"],
        channel["golden_score"],
        channel["date_found"],
    ))
    conn.commit()

def main():
    print("=" * 55)
    print("  YouTube Intelligence - Channel Discovery")
    print("  Niche: History / Mysteries")
    print("=" * 55)

    keywords = [
        "ancient mysteries explained",
        "dark history facts",
        "hidden secrets of history",
        "unsolved mysteries documentary",
        "unknown historical facts",
        "forbidden history",
        "lost civilizations explained",
        "dark secrets of ancient world",
    ]

    conn = init_db()

    channels = search_channels(keywords, max_per_keyword=5)
    print(f"\n Found {len(channels)} unique channels. Scoring now...\n")

    golden = []
    for ch in channels:
        ch = score_channel(ch)
        save_channel(conn, ch)
        tag = "GOLDEN" if ch["golden_score"] >= 50 else "regular"
        print(f"{tag} | Score: {ch['golden_score']:>3} | "
              f"Subs: {ch['subscribers']:>7,} | "
              f"{ch['channel_name']}")
        if ch["golden_score"] >= 50:
            golden.append(ch)

    print(f"\n{'='*55}")
    print(f"  GOLDEN CHANNELS FOUND: {len(golden)}")
    print(f"{'='*55}")
    for g in sorted(golden, key=lambda x: x["golden_score"], reverse=True):
        print(f"\n  Channel  : {g['channel_name']}")
        print(f"  Score    : {g['golden_score']}/100")
        print(f"  Subs     : {g['subscribers']:,}")
        print(f"  Videos   : {g['video_count']}")
        print(f"  Found via: {g['discovered_via']}")
        print(f"  URL      : {g['channel_url']}")

    print(f"\n All data saved to intelligence.db")
    conn.close()

if __name__ == "__main__":
    main()