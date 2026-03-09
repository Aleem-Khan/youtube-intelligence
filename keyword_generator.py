import json
import sqlite3
import requests
from datetime import datetime, timezone
from config import GROQ_API_KEY, NICHE, DB_FILE, GROQ_MODEL


def init_keyword_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keywords (
        keyword     TEXT PRIMARY KEY,
        subtopic    TEXT,
        priority    INTEGER DEFAULT 5,
        searched    INTEGER DEFAULT 0,
        date_added  TEXT
    )''')
    conn.commit()
    return conn


def call_groq(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4000
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def generate_keywords():
    print("\n Asking Groq AI to generate keywords...\n")

    prompt = """You are a YouTube keyword research expert for the History and Mysteries niche.

Generate exactly 300 YouTube search keywords for faceless History and Mystery channels.

Rules:
- Each keyword must be something a real person would search on YouTube
- Keywords should be specific video topics, not broad categories
- Mix these types: dark history, ancient mysteries, forbidden knowledge, lost civilizations, secret societies, unsolved crimes, historical betrayals, ancient weapons, empire collapses, historical cover-ups, archaeological discoveries, mythologies, conspiracies, strange historical events
- Include emotional triggers: dark, secret, hidden, forbidden, unknown, shocking, disturbing, terrifying, mysterious, lost, buried, forgotten
- Keywords should be 3-8 words long

Return ONLY a valid JSON object in this exact format, nothing else:
{
  "subtopics": {
    "Ancient Mysteries": ["keyword1", "keyword2"],
    "Dark History": ["keyword1", "keyword2"],
    "Lost Civilizations": ["keyword1", "keyword2"],
    "Secret Societies": ["keyword1", "keyword2"],
    "Forbidden Knowledge": ["keyword1", "keyword2"],
    "Unsolved Crimes": ["keyword1", "keyword2"],
    "Historical Betrayals": ["keyword1", "keyword2"],
    "Ancient Weapons": ["keyword1", "keyword2"],
    "Empire Collapses": ["keyword1", "keyword2"],
    "Archaeological Discoveries": ["keyword1", "keyword2"],
    "Mythology Explained": ["keyword1", "keyword2"],
    "Historical Conspiracies": ["keyword1", "keyword2"]
  }
}

Each subtopic must have 25 keywords. Total = 300 keywords."""

    raw = call_groq(prompt)
    raw = raw.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    raw = raw[start:end]
    data = json.loads(raw)
    return data["subtopics"]


def save_keywords(conn, subtopics):
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    total = 0
    for subtopic, keywords in subtopics.items():
        for kw in keywords:
            kw = kw.strip()
            if not kw:
                continue
            try:
                c.execute(
                    "INSERT OR IGNORE INTO keywords VALUES (?,?,?,?,?)",
                    (kw, subtopic, 5, 0, now)
                )
                total += 1
            except Exception:
                pass
    conn.commit()
    return total


def print_summary(subtopics):
    print(f"\n{'='*55}")
    print(f"  KEYWORD GENERATION COMPLETE")
    print(f"{'='*55}")
    total = 0
    for subtopic, keywords in subtopics.items():
        print(f"\n  [{subtopic}] — {len(keywords)} keywords")
        for kw in keywords[:3]:
            print(f"    - {kw}")
        if len(keywords) > 3:
            print(f"    ... and {len(keywords)-3} more")
        total += len(keywords)
    print(f"\n  TOTAL KEYWORDS: {total}")
    print(f"{'='*55}\n")


def main():
    print("=" * 55)
    print("  THE GIANT — Keyword Intelligence Engine")
    print(f"  Niche: {NICHE}")
    print("=" * 55)

    if GROQ_API_KEY == "PASTE_YOUR_KEY_HERE":
        print("\n  ERROR: You have not set your Groq API key yet.")
        print("  Open config.py and paste your free key.")
        print("  Get it free at: https://console.groq.com\n")
        return

    conn = init_keyword_db()

    try:
        subtopics = generate_keywords()
        saved = save_keywords(conn, subtopics)
        print_summary(subtopics)
        print(f"  {saved} keywords saved to intelligence.db")
        print(f"  Now run: python giant_finder.py\n")
    except json.JSONDecodeError:
        print("  AI returned bad format. Try running again.")
    except requests.HTTPError as e:
        print(f"  Groq API error: {e}")
        print("  Check your API key in config.py")
    finally:
        conn.close()


if __name__ == "__main__":
    main()