import sqlite3
import os

DB_FILE = "intelligence.db"

print("\n" + "="*55)
print("  THE GIANT — Database Reset Tool")
print("="*55)
print("\n  WARNING: This will delete ALL channel data,")
print("  keywords, and patterns from the database.")
print("  Your .env and Python files will NOT be affected.")
print()

confirm = input("  Type YES to confirm full reset: ").strip()

if confirm != "YES":
    print("\n  Cancelled. Nothing deleted.\n")
    exit()

if not os.path.exists(DB_FILE):
    print(f"\n  No database found at {DB_FILE}. Nothing to delete.\n")
    exit()

conn = sqlite3.connect(DB_FILE)
c    = conn.cursor()

tables = [
    "channels",
    "keywords",
    "niches",
    "videos",
    "channel_titles",
    "title_patterns",
    "thumbnail_patterns",
    "niche_intelligence",
]

deleted = {}
for table in tables:
    try:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        c.execute(f"DELETE FROM {table}")
        deleted[table] = count
        print(f"  Cleared {table:<25} ({count} rows)")
    except Exception:
        pass  # table might not exist yet

conn.commit()
conn.close()

print()
print("  ✓ Database fully reset.")
print("  You can now run discovery fresh from zero.")
print("="*55 + "\n")
