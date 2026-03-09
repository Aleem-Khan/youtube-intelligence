import sqlite3
from config import DB_FILE

def fix():
    print("=" * 55)
    print("  THE GIANT — Database Repair Tool")
    print("=" * 55)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # ── Step 1: Fix keywords table ───────────────────────────────
    print("\n  Step 1: Rebuilding keywords table...")
    try:
        c.execute("ALTER TABLE keywords RENAME TO keywords_old")
        c.execute('''CREATE TABLE keywords (
            keyword    TEXT,
            niche      TEXT,
            subtopic   TEXT,
            searched   INTEGER DEFAULT 0,
            date_added TEXT,
            PRIMARY KEY (keyword, niche)
        )''')
        c.execute('''INSERT OR IGNORE INTO keywords
                     SELECT keyword, niche, subtopic, searched, date_added
                     FROM keywords_old''')
        c.execute("DROP TABLE keywords_old")
        conn.commit()
        print("  Keywords table fixed.")
    except Exception as e:
        print(f"  Keywords already OK or error: {e}")

    # ── Step 2: Fix channels table ───────────────────────────────
    print("\n  Step 2: Rebuilding channels table...")
    try:
        c.execute("ALTER TABLE channels RENAME TO channels_old")
        c.execute('''CREATE TABLE channels (
            channel_id        TEXT PRIMARY KEY,
            channel_name      TEXT,
            channel_url       TEXT,
            niche             TEXT DEFAULT "history and mysteries",
            subscribers       INTEGER,
            total_views       INTEGER,
            video_count       INTEGER,
            discovered_via    TEXT,
            golden_score      INTEGER,
            is_golden         INTEGER DEFAULT 0,
            is_faceless       INTEGER DEFAULT 0,
            faceless_score    INTEGER DEFAULT 0,
            channel_age_days  INTEGER,
            last_video_days   INTEGER,
            date_found        TEXT
        )''')
        try:
            c.execute('''INSERT OR IGNORE INTO channels
                (channel_id, channel_name, channel_url, niche,
                 subscribers, total_views, video_count, discovered_via,
                 golden_score, is_golden, is_faceless, faceless_score,
                 channel_age_days, last_video_days, date_found)
                SELECT channel_id, channel_name, channel_url,
                       COALESCE(niche, "history and mysteries"),
                       subscribers, total_views, video_count, discovered_via,
                       golden_score, is_golden,
                       COALESCE(is_faceless, 0),
                       COALESCE(faceless_score, 0),
                       channel_age_days, last_video_days, date_found
                FROM channels_old''')
        except Exception:
            c.execute('''INSERT OR IGNORE INTO channels
                (channel_id, channel_name, channel_url, niche,
                 subscribers, total_views, video_count, discovered_via,
                 golden_score, is_golden, date_found)
                SELECT channel_id, channel_name, channel_url,
                       "history and mysteries",
                       subscribers, total_views, video_count, discovered_via,
                       golden_score, is_golden, date_found
                FROM channels_old''')
        c.execute("DROP TABLE channels_old")
        conn.commit()
        print("  Channels table fixed.")
    except Exception as e:
        print(f"  Channels already OK or error: {e}")

    # ── Step 3: Fix videos table ─────────────────────────────────
    print("\n  Step 3: Fixing videos table...")
    try:
        c.execute("ALTER TABLE videos RENAME TO videos_old")
        c.execute('''CREATE TABLE videos (
            video_id    TEXT PRIMARY KEY,
            channel_id  TEXT,
            niche       TEXT,
            title       TEXT,
            views       INTEGER,
            upload_date TEXT,
            duration    INTEGER,
            url         TEXT,
            video_score REAL DEFAULT 0
        )''')
        c.execute('''INSERT OR IGNORE INTO videos
                     SELECT video_id, channel_id,
                            COALESCE(niche, "history and mysteries"),
                            title, views, upload_date, duration, url, video_score
                     FROM videos_old''')
        c.execute("DROP TABLE videos_old")
        conn.commit()
        print("  Videos table fixed.")
    except Exception as e:
        print(f"  Videos already OK or error: {e}")

    # ── Step 4: Lower golden score for existing channels ─────────
    print("\n  Step 4: Rescoring existing channels...")
    c.execute('''UPDATE channels SET is_golden = 1
                 WHERE golden_score >= 50''')
    c.execute('''UPDATE channels SET is_golden = 0
                 WHERE golden_score < 50''')
    conn.commit()

    # ── Step 5: Print current stats ──────────────────────────────
    print("\n  Step 5: Current database stats...")
    c.execute("SELECT COUNT(*) FROM channels")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM channels WHERE is_golden=1")
    golden = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM keywords")
    kw = c.fetchone()[0]

    print(f"\n  Total channels  : {total}")
    print(f"  Golden channels : {golden}")
    print(f"  Keywords in DB  : {kw}")

    print(f"\n  Top channels by score:")
    c.execute('''SELECT channel_name, golden_score, subscribers
                 FROM channels ORDER BY golden_score DESC LIMIT 10''')
    for row in c.fetchall():
        print(f"    Score:{row[1]:>3} | Subs:{row[2]:>8,} | {row[0]}")

    conn.close()
    print(f"\n  Database repair complete.")
    print(f"  Now run giant.py and pick any niche.")

if __name__ == "__main__":
    fix()
