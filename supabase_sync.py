"""
supabase_sync.py — THE GIANT Cloud Sync
=========================================
Pushes your local SQLite database to Supabase (free PostgreSQL cloud).
Run this after every discovery session to back up your data.

Setup (one time):
  1. Go to https://supabase.com — create free account
  2. Create new project (free tier — 500MB storage)
  3. Go to Settings → API
  4. Copy "Project URL" → SUPABASE_URL in .env
  5. Copy "anon public" key → SUPABASE_KEY in .env
  6. Run: python supabase_sync.py --setup
     (creates tables in Supabase automatically)
  7. Run: python supabase_sync.py
     (syncs all data)

Usage:
  python supabase_sync.py           sync all channels to cloud
  python supabase_sync.py --setup   create tables in Supabase first
  python supabase_sync.py --status  check connection and row counts
"""

import sqlite3
import requests
import json
import sys
from datetime import datetime
from config import DB_FILE, SUPABASE_URL, SUPABASE_KEY


# ================================================================
#  SUPABASE CLIENT
# ================================================================
class SupabaseClient:
    def __init__(self, url, key):
        self.url = url.rstrip("/")
        self.headers = {
            "apikey":        key,
            "Authorization": f"Bearer {key}",
            "Content-Type":  "application/json",
            "Prefer":        "resolution=merge-duplicates"
        }

    def upsert(self, table, rows):
        """Insert or update rows in a Supabase table"""
        if not rows:
            return 0
        resp = requests.post(
            f"{self.url}/rest/v1/{table}",
            headers=self.headers,
            json=rows,
            timeout=30
        )
        if resp.status_code not in (200, 201):
            raise Exception(f"Supabase upsert failed: {resp.status_code} — {resp.text[:200]}")
        return len(rows)

    def count(self, table):
        """Get row count from a Supabase table"""
        headers = dict(self.headers)
        headers["Prefer"] = "count=exact"
        headers["Range"]  = "0-0"
        resp = requests.get(
            f"{self.url}/rest/v1/{table}?select=channel_id",
            headers=headers,
            timeout=15
        )
        if resp.status_code in (200, 206):
            cr = resp.headers.get("Content-Range", "0/0")
            try:
                return int(cr.split("/")[-1])
            except Exception:
                return 0
        return 0

    def test_connection(self):
        """Test if Supabase connection works"""
        try:
            resp = requests.get(
                f"{self.url}/rest/v1/channels?select=channel_id&limit=1",
                headers=self.headers,
                timeout=10
            )
            return resp.status_code in (200, 206)
        except Exception:
            return False


# ================================================================
#  SETUP — create tables in Supabase
# ================================================================
CHANNELS_SQL = """
create table if not exists channels (
  channel_id       text primary key,
  channel_name     text,
  channel_url      text,
  niche            text,
  subscribers      integer,
  total_views      integer,
  video_count      integer,
  discovered_via   text,
  golden_score     integer,
  is_golden        integer default 0,
  is_faceless      integer default 0,
  faceless_score   integer default 0,
  channel_age_days integer,
  last_video_days  integer,
  date_found       text,
  review_status    text default 'pending',
  recent_views     integer default 0,
  description      text,
  channel_handle   text,
  synced_at        text
);
"""


def run_setup(client):
    """Create required tables in Supabase via SQL editor instructions"""
    print("\n" + "="*58)
    print("  SUPABASE SETUP")
    print("="*58)
    print("""
  Supabase does not allow table creation via REST API.
  You need to run this SQL once in your Supabase dashboard:

  1. Go to https://supabase.com/dashboard
  2. Open your project
  3. Click SQL Editor in the left sidebar
  4. Paste and run this SQL:

  ─────────────────────────────────────────────────────
""")
    print(CHANNELS_SQL)
    print("""  ─────────────────────────────────────────────────────

  After running the SQL, come back here and run:
    python supabase_sync.py --status

  to verify the connection works.
""")


# ================================================================
#  LOAD LOCAL DATA
# ================================================================
def load_local_channels():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM channels")
        rows = [dict(r) for r in c.fetchall()]
    except Exception as e:
        print(f"  Error reading local DB: {e}")
        rows = []
    conn.close()
    return rows


def clean_row(row):
    """Convert row to Supabase-compatible format"""
    cleaned = {}
    for k, v in row.items():
        if v is None:
            cleaned[k] = None
        elif isinstance(v, (int, float)):
            cleaned[k] = v
        else:
            cleaned[k] = str(v)
    cleaned["synced_at"] = datetime.utcnow().isoformat()
    return cleaned


# ================================================================
#  MAIN SYNC
# ================================================================
def sync_to_supabase(verbose=True):
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("\n  [SYNC] Supabase not configured — skipping cloud sync")
        print("  Add SUPABASE_URL and SUPABASE_KEY to .env to enable")
        return False

    client = SupabaseClient(SUPABASE_URL, SUPABASE_KEY)

    if verbose:
        print("\n  [SYNC] Connecting to Supabase...")

    if not client.test_connection():
        print("  [SYNC] Cannot reach Supabase — check URL and key")
        print("  [SYNC] Local data is safe. Skipping cloud sync.")
        return False

    channels = load_local_channels()
    if not channels:
        print("  [SYNC] No channels to sync")
        return True

    if verbose:
        print(f"  [SYNC] Syncing {len(channels)} channels to Supabase...")

    # Upload in batches of 100
    BATCH = 100
    total_synced = 0
    for i in range(0, len(channels), BATCH):
        batch = [clean_row(r) for r in channels[i:i+BATCH]]
        try:
            synced = client.upsert("channels", batch)
            total_synced += synced
            if verbose:
                print(f"  [SYNC] Batch {i//BATCH + 1}: {synced} rows synced")
        except Exception as e:
            print(f"  [SYNC] Batch failed: {e}")

    if verbose:
        print(f"\n  [SYNC] Done — {total_synced} channels in Supabase")

    return True


# ================================================================
#  STATUS CHECK
# ================================================================
def show_status():
    print("\n" + "="*58)
    print("  SUPABASE STATUS CHECK")
    print("="*58)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("""
  NOT CONFIGURED

  Add these to your .env file:
    SUPABASE_URL=https://xxxx.supabase.co
    SUPABASE_KEY=your_anon_key_here

  Get them from:
    supabase.com → Your Project → Settings → API
""")
        return

    print(f"\n  URL : {SUPABASE_URL[:40]}...")
    print(f"  KEY : {SUPABASE_KEY[:20]}...")

    client = SupabaseClient(SUPABASE_URL, SUPABASE_KEY)

    print("\n  Testing connection...")
    if client.test_connection():
        print("  Connection : OK")
        cloud_count = client.count("channels")
        print(f"  Cloud rows : {cloud_count} channels in Supabase")

        # Compare with local
        local = load_local_channels()
        print(f"  Local rows : {len(local)} channels in SQLite")

        if len(local) > cloud_count:
            diff = len(local) - cloud_count
            print(f"\n  {diff} local channels not yet synced.")
            print("  Run: python supabase_sync.py")
        else:
            print("\n  Cloud is up to date.")
    else:
        print("  Connection : FAILED")
        print("  Check your SUPABASE_URL and SUPABASE_KEY")
        print("  Make sure the 'channels' table exists (run --setup first)")

    print()


# ================================================================
#  ENTRY POINT
# ================================================================
if __name__ == "__main__":
    if "--setup" in sys.argv:
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("\n  Add SUPABASE_URL and SUPABASE_KEY to .env first.\n")
        else:
            client = SupabaseClient(SUPABASE_URL, SUPABASE_KEY)
            run_setup(client)

    elif "--status" in sys.argv:
        show_status()

    else:
        print("\n" + "="*58)
        print("  THE GIANT — Supabase Cloud Sync")
        print("="*58)
        success = sync_to_supabase(verbose=True)
        if success:
            print("\n  Your data is now backed up to the cloud.")
        print()
