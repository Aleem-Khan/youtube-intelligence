import re
import json
import sqlite3
import requests
import yt_dlp
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import (
    GROQ_API_KEY, DB_FILE, GROQ_MODEL,
    RESULTS_PER_KEYWORD, PARALLEL_WORKERS,
    GOLDEN_SCORE_MIN, MAX_SUBSCRIBERS, MIN_SUBSCRIBERS,
    MAX_CHANNEL_AGE_DAYS, MAX_LAST_VIDEO_DAYS
)

# ================================================================
#  ALL NICHES — 100+ categories covering every major faceless niche
# ================================================================
ALL_NICHES = {

    "HISTORY & MYSTERIES": [
        "history and mysteries",
        "dark history facts",
        "ancient mysteries",
        "lost civilizations",
        "forbidden history",
        "secret societies",
        "historical conspiracies",
        "unsolved historical mysteries",
        "ancient weapons and warfare",
        "empire collapses explained",
        "archaeological discoveries",
        "mythology explained",
        "historical betrayals",
        "medieval dark history",
        "world war secrets",
        "cold war mysteries",
        "ancient egypt secrets",
        "roman empire dark facts",
        "viking history explained",
        "ancient greece mysteries",
    ],

    "TRUE CRIME & DARK": [
        "true crime documentaries",
        "unsolved murders explained",
        "serial killers psychology",
        "cold case mysteries",
        "criminal masterminds",
        "dark web explained",
        "prison documentaries",
        "notorious criminals history",
        "forensic science explained",
        "cult leaders exposed",
        "kidnapping cases explained",
        "heist stories explained",
        "con artists exposed",
        "dark psychology tactics",
        "criminal profiling explained",
    ],

    "PSYCHOLOGY & MIND": [
        "psychology and human behavior",
        "dark psychology explained",
        "manipulation tactics exposed",
        "cognitive biases explained",
        "social psychology facts",
        "narcissism explained",
        "mental health explained",
        "subconscious mind explained",
        "body language secrets",
        "emotional intelligence",
        "overthinking psychology",
        "dopamine and addiction",
        "attachment styles explained",
        "trauma psychology",
        "persuasion psychology",
        "human memory explained",
        "sleep psychology facts",
        "fear psychology explained",
        "introvert psychology",
        "stoicism explained",
    ],

    "SCIENCE & SPACE": [
        "space exploration facts",
        "universe mysteries explained",
        "black holes explained",
        "quantum physics simplified",
        "dark matter explained",
        "alien life possibilities",
        "mars exploration secrets",
        "nasa hidden facts",
        "multiverse theory explained",
        "time travel physics",
        "evolution explained simply",
        "ocean mysteries unexplained",
        "earth science mysteries",
        "physics of impossible",
        "future technology explained",
        "artificial intelligence explained",
        "genetics explained simply",
        "climate science explained",
        "nuclear science explained",
        "biology mysteries explained",
    ],

    "FINANCE & MONEY": [
        "finance and money explained",
        "how billionaires think",
        "stock market explained",
        "passive income secrets",
        "financial freedom explained",
        "investing for beginners",
        "crypto explained simply",
        "real estate investing secrets",
        "how banks work explained",
        "economic collapse explained",
        "poverty mindset explained",
        "dark side of capitalism",
        "tax secrets of the rich",
        "financial manipulation exposed",
        "how money really works",
        "hedge funds explained",
        "dark side of wall street",
        "world economy secrets",
        "inflation explained simply",
        "debt trap explained",
    ],

    "MOTIVATION & MINDSET": [
        "motivation and mindset",
        "success habits explained",
        "discipline over motivation",
        "stoic philosophy life",
        "growth mindset explained",
        "morning routines of successful",
        "self improvement psychology",
        "productivity secrets explained",
        "time management mastery",
        "overcoming failure stories",
        "mental toughness training",
        "focus and deep work",
        "minimalism lifestyle explained",
        "atomic habits explained",
        "comfort zone psychology",
        "confidence building explained",
    ],

    "PHILOSOPHY & WISDOM": [
        "philosophy explained simply",
        "existentialism explained",
        "stoicism life philosophy",
        "nihilism explained simply",
        "ancient wisdom explained",
        "meaning of life philosophy",
        "ethics and morality explained",
        "consciousness explained",
        "free will vs determinism",
        "buddhist philosophy explained",
        "greek philosophy explained",
        "eastern philosophy secrets",
        "philosophy of death",
        "logic and reasoning explained",
    ],

    "GEOPOLITICS & POWER": [
        "geopolitics explained simply",
        "world power secrets",
        "hidden political agendas",
        "superpower conflicts explained",
        "intelligence agencies secrets",
        "cia operations exposed",
        "political corruption exposed",
        "how governments manipulate",
        "propaganda techniques exposed",
        "surveillance state explained",
        "world war three risks",
        "nuclear war threats explained",
        "economic warfare explained",
        "shadow governments explained",
        "military secrets exposed",
    ],

    "HEALTH & LONGEVITY": [
        "health and longevity secrets",
        "longevity science explained",
        "fasting science explained",
        "gut health explained",
        "cancer prevention facts",
        "sleep optimization science",
        "brain health explained",
        "anti aging science",
        "nutrition myths debunked",
        "exercise science explained",
        "mental health improvement",
        "addiction science explained",
        "stress biology explained",
        "immune system explained",
        "hormone optimization explained",
    ],

    "DARK BIOGRAPHIES": [
        "dark biographies of powerful people",
        "dictators explained",
        "rise and fall of empires",
        "corrupt leaders exposed",
        "mafia bosses explained",
        "warlords of history",
        "rise of serial killers",
        "cult leaders psychology",
        "dark side of celebrities",
        "tragic genius stories",
        "betrayed leaders history",
        "fallen empires leaders",
        "criminal masterminds biographies",
    ],

    "TECHNOLOGY & FUTURE": [
        "future technology explained",
        "artificial intelligence dangers",
        "robots replacing humans",
        "silicon valley secrets",
        "big tech manipulation exposed",
        "surveillance technology explained",
        "social media psychology",
        "algorithm manipulation exposed",
        "hacking explained simply",
        "cybersecurity threats explained",
        "metaverse explained simply",
        "blockchain explained simply",
        "elon musk technology plans",
        "future of humanity explained",
    ],

    "RELIGION & SPIRITUALITY": [
        "religion mysteries explained",
        "forbidden religious texts",
        "bible mysteries explained",
        "ancient religions explained",
        "religious conspiracies exposed",
        "occult history explained",
        "secret religious orders",
        "afterlife beliefs explained",
        "pagan religions explained",
        "lost religious scriptures",
        "religious dark history",
        "mysticism explained simply",
    ],

    "NATURE & ANIMALS": [
        "nature mysteries unexplained",
        "animal intelligence explained",
        "ocean creatures explained",
        "apex predators explained",
        "animal psychology explained",
        "extinction events explained",
        "dangerous animals explained",
        "prehistoric animals explained",
        "animal behavior secrets",
        "deep sea mysteries",
    ],

    "ECONOMICS & SOCIETY": [
        "society manipulation explained",
        "class system exposed",
        "education system dark truth",
        "media manipulation tactics",
        "consumerism psychology",
        "corporate greed exposed",
        "poverty trap explained",
        "inequality explained simply",
        "housing crisis explained",
        "food industry secrets",
        "pharmaceutical industry secrets",
        "social engineering explained",
    ],

    "WAR & MILITARY": [
        "war history explained",
        "military secrets exposed",
        "special forces explained",
        "psychological warfare explained",
        "weapons technology explained",
        "spy operations explained",
        "battle strategies explained",
        "war crimes history",
        "guerrilla warfare explained",
        "nuclear weapons history",
        "cold war operations",
        "world war untold stories",
    ],
}


# ================================================================
#  FACELESS DETECTION
# ================================================================
FACELESS_SIGNALS = [
    "animated", "animation", "narrator", "narration", "explained",
    "documentary", "history", "mystery", "mysteries", "facts",
    "ancient", "secret", "hidden", "forbidden", "unknown",
    "dark", "lost", "empire", "civilization", "archaeology",
    "myth", "conspiracy", "unsolved", "betrayal", "psychology",
    "crime", "science", "space", "philosophy", "finance", "money",
    "truth", "power", "war", "political", "motivation", "mindset",
    "biography", "story", "stories", "tale", "tales", "archive",
    "education", "educational", "learning", "knowledge", "insight",
    "explained", "simplified", "analysis", "breakdown", "deep dive"
]

FACE_SIGNALS = [
    "vlog", "reaction", "podcast", "interview", "gaming",
    "cooking", "makeup", "beauty", "fitness", "workout",
    "family", "kids", "prank", "challenge", "funny", "comedy",
    "music", "song", "dance", "travel", "food", "review", "unboxing"
]


# ================================================================
#  DATABASE
# ================================================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS niches (
        niche      TEXT PRIMARY KEY,
        date_added TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS keywords (
        keyword    TEXT,
        niche      TEXT,
        subtopic   TEXT,
        searched   INTEGER DEFAULT 0,
        date_added TEXT,
        PRIMARY KEY (keyword, niche)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS channels (
        channel_id        TEXT PRIMARY KEY,
        channel_name      TEXT,
        channel_url       TEXT,
        niche             TEXT,
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

    c.execute('''CREATE TABLE IF NOT EXISTS videos (
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

    conn.commit()
    return conn


def save_niche(conn, niche):
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO niches VALUES (?,?)",
              (niche, datetime.now(timezone.utc).isoformat()))
    conn.commit()


# ================================================================
#  NICHE SELECTION MENU
# ================================================================
def show_niche_menu():
    print()
    print("=" * 65)
    print("  THE GIANT — YouTube Intelligence System")
    print("  Select a niche to research")
    print("=" * 65)

    categories = list(ALL_NICHES.keys())
    all_niches_flat = []
    counter = 1

    for cat in categories:
        print(f"\n  --- {cat} ---")
        for niche in ALL_NICHES[cat]:
            print(f"  [{counter:>3}]  {niche}")
            all_niches_flat.append(niche)
            counter += 1

    print()
    print(f"  [  0]  Enter a custom niche not in this list")
    print()
    print("=" * 65)

    choice = input("  Enter number (or 0 for custom): ").strip()

    if choice == "0":
        custom = input("  Type your custom niche: ").strip().lower()
        return custom if custom else "history and mysteries"

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(all_niches_flat):
            return all_niches_flat[idx]
        else:
            print("  Invalid number. Using history and mysteries.")
            return "history and mysteries"
    except ValueError:
        print("  Invalid input. Using history and mysteries.")
        return "history and mysteries"


# ================================================================
#  GROQ AI — KEYWORD GENERATION
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
        "temperature": 0.7,
        "max_tokens":  4000
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def generate_keywords(niche):
    print(f"\n  Generating 300 keywords for: {niche.upper()}")

    prompt = f"""You are a YouTube keyword research expert.

Generate exactly 300 YouTube search keywords for faceless channels in this niche: {niche}

Rules:
- Keywords must be what real people search on YouTube
- Be very specific not broad
- Include emotional triggers: dark, secret, hidden, forbidden, shocking, disturbing, terrifying, mysterious, lost, forgotten, exposed
- Keywords should be 3 to 8 words long
- Make them highly clickable and specific

Return ONLY valid JSON in this exact format with no extra text:
{{
  "subtopics": {{
    "Subtopic 1": ["keyword1", "keyword2", "keyword3"],
    "Subtopic 2": ["keyword1", "keyword2", "keyword3"],
    "Subtopic 3": ["keyword1", "keyword2", "keyword3"],
    "Subtopic 4": ["keyword1", "keyword2", "keyword3"],
    "Subtopic 5": ["keyword1", "keyword2", "keyword3"],
    "Subtopic 6": ["keyword1", "keyword2", "keyword3"],
    "Subtopic 7": ["keyword1", "keyword2", "keyword3"],
    "Subtopic 8": ["keyword1", "keyword2", "keyword3"],
    "Subtopic 9": ["keyword1", "keyword2", "keyword3"],
    "Subtopic 10": ["keyword1", "keyword2", "keyword3"],
    "Subtopic 11": ["keyword1", "keyword2", "keyword3"],
    "Subtopic 12": ["keyword1", "keyword2", "keyword3"]
  }}
}}

Create 12 subtopics specific to: {niche}
Each subtopic must have exactly 25 keywords.
Total must be 300 keywords."""

    raw   = call_groq(prompt)
    raw   = raw.strip()
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    raw   = raw[start:end]
    data  = json.loads(raw)
    return data["subtopics"]


def save_keywords(conn, niche, subtopics):
    c   = conn.cursor()
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
                    (kw, niche, subtopic, 0, now)
                )
                total += 1
            except Exception:
                pass
    conn.commit()
    return total


def load_keywords(conn, niche):
    c = conn.cursor()
    c.execute(
        "SELECT keyword, subtopic FROM keywords WHERE niche=? AND searched=0",
        (niche,)
    )
    rows = c.fetchall()
    if not rows:
        c.execute("UPDATE keywords SET searched=0 WHERE niche=?", (niche,))
        conn.commit()
        c.execute(
            "SELECT keyword, subtopic FROM keywords WHERE niche=? AND searched=0",
            (niche,)
        )
        rows = c.fetchall()
    return rows


def mark_searched(conn, keyword, niche):
    c = conn.cursor()
    c.execute(
        "UPDATE keywords SET searched=1 WHERE keyword=? AND niche=?",
        (keyword, niche)
    )
    conn.commit()


# ================================================================
#  FACELESS DETECTION
# ================================================================
def detect_faceless(name, desc):
    text = (name + " " + desc).lower()
    face_hits     = sum(1 for s in FACE_SIGNALS    if s in text)
    faceless_hits = sum(1 for s in FACELESS_SIGNALS if s in text)
    if face_hits >= 2:
        return False, 0
    score = min(faceless_hits * 10, 100)
    return score >= 30, score


# ================================================================
#  YOUTUBE SEARCH
# ================================================================
def search_keyword(keyword, max_results=20):
    found    = {}
    ydl_opts = {
        "quiet":          True,
        "no_warnings":    True,
        "extract_flat":   True,
        "playlist_items": f"1-{max_results}",
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(
                f"ytsearch{max_results}:{keyword}", download=False
            )
        for entry in (result.get("entries") or []):
            if not entry:
                continue
            cid  = entry.get("channel_id")
            curl = entry.get("channel_url")
            if cid and curl and cid not in found:
                found[cid] = {
                    "channel_id":     cid,
                    "channel_name":   entry.get("channel", "Unknown"),
                    "channel_url":    curl,
                    "discovered_via": keyword,
                }
    except Exception as e:
        print(f"  Search error: {e}")
    return found


# ================================================================
#  FAST DATE CHECK — Uses YouTube RSS with real channel_id
#  channel_id is UCxxxx format from search results — always works
# ================================================================
def get_channel_dates_fast(channel_id):

    if not channel_id or not channel_id.startswith("UC"):
        return None, None

    try:
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp    = requests.get(rss_url, headers=headers, timeout=12)

        if resp.status_code != 200:
            return None, None

        # RSS returns newest ~15 videos with exact published dates
        published_dates = re.findall(r"<published>(\d{4}-\d{2}-\d{2})", resp.text)

        if not published_dates:
            return None, None

        dates = []
        for d in published_dates:
            try:
                dates.append(
                    datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                )
            except ValueError:
                pass

        if dates:
            return min(dates), max(dates)

    except Exception:
        pass

    return None, None


# ================================================================
#  GOLDEN SCORE — v5 FINAL
#
#  Core logic: AGE + VPV combined = the real signal
#
#  0–90 days   + high VPV = VIP GOLDEN  (found early, formula working)
#  91–180 days + high VPV = GOLDEN      (still growing, good signal)
#  181–365 days + very high VPV = PROMISING (mature but useful intel)
#  365+ days   = hard rejected before scoring
#
#  Agent Flappy: 270 days, 598k VPV → GOLDEN (exceptional VPV saves it)
#  Space Guy:     44 days,  59k VPV → VIP GOLDEN (young + growing fast)
# ================================================================
def calculate_golden_score(subs, vid_count, view_count,
                            age_days, last_video_days,
                            faceless_score):
    score = 0
    vpv   = view_count / max(vid_count, 1) if vid_count > 0 else 0

    # ── 1. AGE + VPV COMBINED — the core signal (max 45) ─────────
    # Young channel growing fast = the most valuable find
    # Older channel needs much higher VPV to still qualify
    if age_days is not None:
        if age_days <= 90:
            # VIP zone — any decent VPV is exciting here
            if vpv >= 200000:   score += 45
            elif vpv >= 100000: score += 40
            elif vpv >= 50000:  score += 35
            elif vpv >= 20000:  score += 28
            elif vpv >= 5000:   score += 18
            elif vpv >= 1000:   score += 8
        elif age_days <= 180:
            # Golden zone — needs stronger VPV to qualify
            if vpv >= 500000:   score += 40
            elif vpv >= 200000: score += 33
            elif vpv >= 100000: score += 26
            elif vpv >= 50000:  score += 18
            elif vpv >= 20000:  score += 10
            elif vpv >= 5000:   score += 4
        elif age_days <= 365:
            # Mature zone — only very high VPV is worth noting
            if vpv >= 500000:   score += 30
            elif vpv >= 200000: score += 20
            elif vpv >= 100000: score += 12
            elif vpv >= 50000:  score += 5
            # below 50k VPV at this age = not golden, gets 0
    else:
        # Age unknown — use VPV alone, conservative scoring
        if vpv >= 500000:       score += 25
        elif vpv >= 200000:     score += 18
        elif vpv >= 100000:     score += 12
        elif vpv >= 50000:      score += 7

    # ── 2. Subscriber range (max 15) ─────────────────────────────
    if 5000 <= subs <= 100000:
        score += 15
    elif 100000 < subs <= 250000:
        score += 9
    elif 250000 < subs <= 500000:
        score += 3

    # ── 3. Video count — fewer + high VPV = formula found (max 15)
    if 5 <= vid_count <= 30:
        score += 15
    elif 31 <= vid_count <= 60:
        score += 8
    elif 61 <= vid_count <= 100:
        score += 2
    # 100+ gets 0

    # ── 4. Recent activity — must be uploading now (max 15) ──────
    if last_video_days is not None:
        if last_video_days <= 7:
            score += 15
        elif last_video_days <= 14:
            score += 10
        elif last_video_days <= 30:
            score += 5

    # ── 5. Faceless confidence (max 10) ──────────────────────────
    if faceless_score >= 70:
        score += 10
    elif faceless_score >= 50:
        score += 7
    elif faceless_score >= 30:
        score += 3

    return min(score, 100)


# ================================================================
#  CHANNEL SCORER
# ================================================================
def score_channel(channel, niche):
    now      = datetime.now(timezone.utc)
    ydl_opts = {
        "quiet":        True,
        "no_warnings":  True,
        "extract_flat": True,
        "playlistend":  1,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel["channel_url"], download=False)

        subs       = info.get("channel_follower_count") or 0
        view_count = info.get("view_count") or 0
        vid_count  = info.get("playlist_count") or 0
        name       = info.get("channel") or channel["channel_name"]
        desc       = info.get("description") or ""
        language   = info.get("language") or ""

        # ── ENGLISH ONLY FILTER ───────────────────────────────────
        # Reject if yt-dlp reports a clearly non-English language tag
        if language and language not in ("en", "en-US", "en-GB", "en-AU",
                                          "en-CA", "en-IN", "", None):
            return None

        # Script-based detection — counts foreign characters as a percentage
        # of total letters. Rejects only if clearly non-English.
        # Threshold: >25% of channel name OR >40% of description = foreign channel
        # This allows occasional foreign symbols, emojis, or mixed-script logos
        def foreign_script_ratio(text):
            if not text:
                return 0.0
            letter_count   = 0
            foreign_count  = 0
            for ch in text:
                cp = ord(ch)
                # Skip spaces, punctuation, numbers, emojis — only count letters
                if cp < 128:
                    if ch.isalpha():
                        letter_count += 1
                    continue
                # Foreign script ranges
                if (
                    0x0600 <= cp <= 0x06FF or   # Arabic / Persian / Urdu
                    0x0900 <= cp <= 0x097F or   # Devanagari (Hindi)
                    0x0980 <= cp <= 0x09FF or   # Bengali
                    0x0B80 <= cp <= 0x0BFF or   # Tamil
                    0x0C00 <= cp <= 0x0C7F or   # Telugu
                    0x0400 <= cp <= 0x04FF or   # Cyrillic (Russian etc.)
                    0x0E00 <= cp <= 0x0E7F or   # Thai
                    0x0590 <= cp <= 0x05FF or   # Hebrew
                    0x4E00 <= cp <= 0x9FFF or   # Chinese (CJK)
                    0x3040 <= cp <= 0x30FF or   # Japanese (Hiragana/Katakana)
                    0xAC00 <= cp <= 0xD7AF or   # Korean (Hangul)
                    0x0A80 <= cp <= 0x0AFF or   # Gujarati
                    0x0A00 <= cp <= 0x0A7F      # Gurmukhi (Punjabi)
                ):
                    foreign_count += 1
                    letter_count  += 1
            if letter_count == 0:
                return 0.0
            return foreign_count / letter_count

        name_ratio = foreign_script_ratio(name)
        desc_ratio = foreign_script_ratio(desc[:300])

        # Reject if channel name is >25% foreign OR description is >40% foreign
        if name_ratio > 0.25 or desc_ratio > 0.40:
            return None

        if subs > MAX_SUBSCRIBERS or (subs > 0 and subs < MIN_SUBSCRIBERS):
            return None

        # Hard reject: 100+ videos with under 150k subs = slow grower pattern
        if vid_count > 100 and subs < 150000:
            return None

        is_faceless, faceless_score = detect_faceless(name, desc)
        if not is_faceless:
            return None

        # Use channel_id directly for RSS — this is the UCxxxx ID from search
        cid                   = channel["channel_id"]
        first_date, last_date = get_channel_dates_fast(cid)
        age_days              = None
        last_video_days       = None

        if last_date is not None:
            last_video_days = (now - last_date).days
            if last_video_days > MAX_LAST_VIDEO_DAYS:
                return None

        if first_date is not None:
            oldest_rss_days = (now - first_date).days
            # RSS only returns the 15 most recent videos.
            # If channel has more than 15 videos, min(RSS dates) is NOT the
            # first video date — it is the 15th most recent video.
            # Extrapolate the real channel age using upload frequency.
            if vid_count > 15:
                age_days = int(oldest_rss_days * vid_count / 15)
            else:
                age_days = oldest_rss_days
            if age_days > MAX_CHANNEL_AGE_DAYS:
                return None

        golden_score = calculate_golden_score(
            subs, vid_count, view_count,
            age_days, last_video_days,
            faceless_score
        )

        return {
            "channel_id":       channel["channel_id"],
            "channel_name":     name,
            "channel_url":      channel["channel_url"],
            "niche":            niche,
            "subscribers":      subs,
            "total_views":      view_count,
            "video_count":      vid_count,
            "discovered_via":   channel["discovered_via"],
            "golden_score":     golden_score,
            "is_golden":        1 if golden_score >= GOLDEN_SCORE_MIN else 0,
            "is_faceless":      1,
            "faceless_score":   faceless_score,
            "channel_age_days": age_days,
            "last_video_days":  last_video_days,
            "date_found":       now.isoformat(),
        }

    except Exception:
        return None


# ================================================================
#  SAVE CHANNEL
# ================================================================
def channel_exists(conn, channel_id):
    c = conn.cursor()
    c.execute("SELECT 1 FROM channels WHERE channel_id=?", (channel_id,))
    return c.fetchone() is not None


def save_channel(conn, ch):
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO channels VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        ch["channel_id"],
        ch["channel_name"],
        ch["channel_url"],
        ch["niche"],
        ch["subscribers"],
        ch["total_views"],
        ch["video_count"],
        ch["discovered_via"],
        ch["golden_score"],
        ch["is_golden"],
        ch["is_faceless"],
        ch["faceless_score"],
        ch.get("channel_age_days"),
        ch.get("last_video_days"),
        ch["date_found"],
    ))
    conn.commit()


# ================================================================
#  PRINT STATUS
# ================================================================
def print_status(ch):
    score    = ch["golden_score"]
    subs     = ch["subscribers"]
    name     = ch["channel_name"]
    age      = ch.get("channel_age_days")
    last     = ch.get("last_video_days")
    age_str  = f"{age}d"  if age  is not None else "?d"
    last_str = f"{last}d" if last is not None else "?d"

    if score >= GOLDEN_SCORE_MIN:
        tag = "*** GOLDEN ***"
    elif score >= 35:
        tag = ">> PROMISING  "
    else:
        tag = "   regular    "

    print(f"  {tag} | Score:{score:>3} | Age:{age_str:>5} "
          f"| Last:{last_str:>5} | Subs:{subs:>8,} | {name}")


# ================================================================
#  DATABASE SUMMARY
# ================================================================
def show_summary(conn):
    c = conn.cursor()
    c.execute('''SELECT niche, COUNT(*) as total, SUM(is_golden) as golden
                 FROM channels GROUP BY niche ORDER BY golden DESC''')
    rows = c.fetchall()
    if rows:
        print(f"\n  {'='*65}")
        print(f"  FULL DATABASE SUMMARY — ALL NICHES")
        print(f"  {'='*65}")
        print(f"  {'NICHE':<38} {'CHANNELS':>8} {'GOLDEN':>8}")
        print(f"  {'-'*58}")
        for row in rows:
            print(f"  {row[0]:<38} {row[1]:>8} {row[2]:>8}")

    c.execute("SELECT COUNT(*) FROM channels")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM channels WHERE is_golden=1")
    gold  = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT niche) FROM channels")
    niches = c.fetchone()[0]
    print(f"\n  Total channels     : {total}")
    print(f"  Total golden       : {gold}")
    print(f"  Total niches       : {niches}")


# ================================================================
#  MAIN
# ================================================================
def main():
    conn  = init_db()
    niche = show_niche_menu()
    save_niche(conn, niche)

    print(f"\n  Selected: {niche.upper()}")
    keywords = load_keywords(conn, niche)

    if not keywords:
        print(f"  No keywords yet. Generating now...")
        try:
            subtopics = generate_keywords(niche)
            saved     = save_keywords(conn, niche, subtopics)
            print(f"  {saved} keywords generated.")
            keywords  = load_keywords(conn, niche)
        except (json.JSONDecodeError, requests.HTTPError) as e:
            print(f"  Keyword generation failed: {e}")
            conn.close()
            return
    else:
        print(f"  {len(keywords)} keywords ready to search.")

    total_kw = len(keywords)
    print(f"\n  Keywords         : {total_kw}")
    print(f"  Results/keyword  : {RESULTS_PER_KEYWORD}")
    print(f"  Parallel workers : {PARALLEL_WORKERS}")
    print(f"  Age filter       : max {MAX_CHANNEL_AGE_DAYS} days")
    print(f"  Activity filter  : last video max {MAX_LAST_VIDEO_DAYS} days")
    print(f"  Faceless filter  : ON")
    print(f"  Golden threshold : {GOLDEN_SCORE_MIN}/100")
    print(f"\n  Starting...\n")
    print("-" * 70)

    all_found   = {}
    golden_list = []

    for idx, (keyword, subtopic) in enumerate(keywords, 1):
        print(f"\n[{idx}/{total_kw}] {keyword}")

        found        = search_keyword(keyword, RESULTS_PER_KEYWORD)
        new_channels = {
            cid: ch for cid, ch in found.items()
            if cid not in all_found and not channel_exists(conn, cid)
        }
        all_found.update(found)

        if not new_channels:
            mark_searched(conn, keyword, niche)
            continue

        print(f"  {len(new_channels)} new channels to check")

        with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as ex:
            futures = {
                ex.submit(score_channel, ch, niche): cid
                for cid, ch in new_channels.items()
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result is None:
                        continue
                    save_channel(conn, result)
                    print_status(result)
                    if result["is_golden"]:
                        golden_list.append(result)
                except Exception:
                    pass

        mark_searched(conn, keyword, niche)
        time.sleep(0.3)

    print(f"\n{'='*70}")
    print(f"  COMPLETE — {niche.upper()}")
    print(f"{'='*70}")
    print(f"  Keywords searched : {total_kw}")
    print(f"  Golden this run   : {len(golden_list)}")

    if golden_list:
        print(f"\n  GOLDEN CHANNELS FOUND")
        print(f"  {'='*60}")
        for g in sorted(golden_list, key=lambda x: x["golden_score"], reverse=True):
            print(f"\n  Channel  : {g['channel_name']}")
            print(f"  Score    : {g['golden_score']}/100")
            print(f"  Age      : {g.get('channel_age_days')} days")
            print(f"  Last vid : {g.get('last_video_days')} days ago")
            print(f"  Subs     : {g['subscribers']:,}")
            print(f"  Videos   : {g['video_count']}")
            print(f"  URL      : {g['channel_url']}")

    show_summary(conn)
    print(f"\n  Data saved to {DB_FILE}")
    conn.close()


if __name__ == "__main__":
    main()
