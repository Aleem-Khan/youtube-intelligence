import re
import json
import sqlite3
import requests
import yt_dlp
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from faceless_detector import detect_faceless_full
from config import (
    GROQ_API_KEY, DB_FILE, GROQ_MODEL, GROQ_MODEL_FAST,
    RESULTS_PER_KEYWORD, PARALLEL_WORKERS,
    GOLDEN_SCORE_MIN, PROMISING_SCORE_MIN,
    MAX_SUBSCRIBERS, MIN_SUBSCRIBERS,
    MAX_CHANNEL_AGE_DAYS, MAX_LAST_VIDEO_DAYS
)
from ai_router import call_ai

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

    # ── NEW NICHES FROM GEMINI 2026 RESEARCH ─────────────────────

    "HUMAN BEHAVIOR & DARK PSYCHOLOGY": [
        "dark psychology manipulation tactics",
        "why people lie psychology",
        "psychological triggers explained",
        "cult leader manipulation tactics",
        "body language secrets exposed",
        "narcissist behavior exposed",
        "social engineering explained",
        "mind control techniques history",
        "toxic behavior patterns explained",
        "gaslighting psychology explained",
        "psychopath traits explained",
        "emotional manipulation tactics",
        "stockholm syndrome explained",
        "mob mentality psychology",
        "revenge psychology explained",
    ],

    "MICRO HISTORY & DIGITAL ARCHAEOLOGY": [
        "forgotten internet history explained",
        "lost media mysteries explained",
        "dark web mysteries documentary",
        "internet mysteries unsolved cases",
        "abandoned websites history",
        "viral moments origin stories",
        "old youtube era explained",
        "early internet dark stories",
        "digital history lost content",
        "cicada 3301 mystery explained",
        "internet rabbit holes explained",
        "web 1.0 nostalgia history",
        "forgotten tech history",
        "online mystery solved explained",
        "creepypasta origins explained",
    ],

    "RESTORATION & SATISFYING": [
        "vintage item restoration satisfying",
        "antique restoration documentary",
        "old console restoration video",
        "typewriter restoration satisfying",
        "abandoned object restored video",
        "rusty tool restoration satisfying",
        "vintage car restoration documentary",
        "forgotten object restoration",
        "satisfying restoration transformation",
        "historical artifact restoration",
        "old radio restoration satisfying",
        "broken antique restored video",
    ],

    "NICHE TECH TUTORIALS": [
        "trading app tutorial for beginners",
        "notion workflow explained simply",
        "obsidian productivity tutorial",
        "productivity tool walkthrough",
        "binance tutorial step by step",
        "clickup workflow tutorial",
        "automation tools explained simply",
        "AI tools for beginners guide",
        "robinhood investing tutorial",
        "webull tutorial beginners",
        "make money with AI tools",
        "passive income AI automation",
        "digital tools explained simply",
    ],

    "GEOPOLITICAL STORYTELLING": [
        "geopolitics explained documentary",
        "world history predictions explained",
        "empire rise and fall history",
        "cold war untold stories",
        "modern war explained documentary",
        "superpower rivalry history",
        "economic collapse history explained",
        "border conflict history explained",
        "forgotten wars history",
        "proxy war history explained",
        "regime change history",
        "resource wars history explained",
        "diplomatic secrets history",
        "revolution history explained",
    ],

    "AMBIENT & LOFI": [
        "lofi music study ambience",
        "meditative urban ambience video",
        "rain sounds study music",
        "coffee shop ambience lofi",
        "night city ambience relaxing",
        "medieval tavern ambience",
        "fantasy world ambience music",
        "cozy reading ambience music",
        "japanese city ambience lofi",
        "dark academia ambience music",
    ],

    "CORPORATE SCANDALS": [
        "corporate fraud exposed documentary",
        "company downfall explained",
        "financial scandal history",
        "startup failure explained",
        "ponzi scheme history explained",
        "wall street scandal exposed",
        "biggest corporate lies exposed",
        "enron scandal explained",
        "crypto scam exposed history",
        "billion dollar fraud exposed",
        "corporate crime documentary",
        "ceo downfall story explained",
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

# News aggregator signals — reuse clips, get demonetized, no original value
NEWS_SIGNALS = [
    "breaking news", "news today", "latest news", "news update",
    "daily news", "world news", "news channel", "news network",
    "top stories", "headlines", "live news", "news report",
    "current events", "news clips", "news highlights",
    "political news", "election news", "news compilation",
    "viral news", "trending news", "tv news", "cable news"
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
        date_found        TEXT,
        review_status     TEXT DEFAULT 'pending',
        recent_views      INTEGER DEFAULT 0,
        description       TEXT,
        channel_handle    TEXT
    )''')

    # ── Auto-migrate existing databases ──────────────────────────
    migrations = [
        "ALTER TABLE channels ADD COLUMN review_status TEXT DEFAULT 'pending'",
        "ALTER TABLE channels ADD COLUMN recent_views INTEGER DEFAULT 0",
        "ALTER TABLE channels ADD COLUMN description TEXT",
        "ALTER TABLE channels ADD COLUMN channel_handle TEXT",
    ]
    for sql in migrations:
        try:
            c.execute(sql)
        except Exception:
            pass  # column already exists

    c.execute('''CREATE TABLE IF NOT EXISTS videos (
        video_id      TEXT PRIMARY KEY,
        channel_id    TEXT,
        niche         TEXT,
        title         TEXT,
        views         INTEGER,
        likes         INTEGER DEFAULT 0,
        comments      INTEGER DEFAULT 0,
        upload_date   TEXT,
        duration      INTEGER,
        url           TEXT,
        thumbnail_url TEXT,
        description   TEXT,
        tags          TEXT,
        video_score   REAL DEFAULT 0,
        outlier_score REAL DEFAULT 0,
        date_scraped  TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS patterns (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        niche         TEXT,
        pattern_type  TEXT,
        pattern_value TEXT,
        frequency     INTEGER DEFAULT 1,
        avg_views     INTEGER DEFAULT 0,
        date_found    TEXT
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
#  AI KEYWORD GENERATION  —  uses ai_router (Groq → Gemini fallback)
# ================================================================


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

    raw   = call_ai(prompt)
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
    text      = (name + " " + desc).lower()
    name_text = name.lower()

    # Reject news aggregator channels immediately
    # 1 match in channel NAME alone is enough — news in name = news channel
    name_news_hits = sum(1 for s in NEWS_SIGNALS if s in name_text)
    if name_news_hits >= 1:
        return False, 0

    # 2 matches in full text (name + desc) = news channel
    full_news_hits = sum(1 for s in NEWS_SIGNALS if s in text)
    if full_news_hits >= 2:
        return False, 0

    face_hits     = sum(1 for s in FACE_SIGNALS     if s in text)
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
        "ignoreerrors":   True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(
                f"ytsearch{max_results}:{keyword}", download=False
            )
        for entry in (result.get("entries") or []):
            if not entry:
                continue
            curl = entry.get("channel_url") or ""
            cid  = entry.get("channel_id")  or ""

            # Try to get UCxxxx from channel_url directly
            url_match = re.search(r"channel/(UC[A-Za-z0-9_-]{20,})", curl)
            if url_match:
                cid = url_match.group(1)
            elif not cid.startswith("UC"):
                # channel_url is a handle like /@name — use uploader_id or channel_id
                uploader_id = entry.get("uploader_id") or ""
                if uploader_id.startswith("UC"):
                    cid = uploader_id
                # Rebuild a proper /channel/ URL if we have UCxxxx
                if cid.startswith("UC"):
                    curl = f"https://www.youtube.com/channel/{cid}"

            if cid and cid.startswith("UC") and curl and cid not in found:
                found[cid] = {
                    "channel_id":     cid,
                    "channel_name":   entry.get("channel", "Unknown"),
                    "channel_url":    f"https://www.youtube.com/channel/{cid}",
                    "discovered_via": keyword,
                }
    except Exception as e:
        print(f"  Search error: {e}")
    return found


# ================================================================
#  DATE + VIEW FETCH — Uses yt-dlp to get last video date and
#  estimate channel age. RSS is blocked in some regions so we
#  fetch the last 15 videos directly via yt-dlp.
# ================================================================
def parse_relative_date(text):
    if not text:
        return None
    text = text.lower().strip()
    now  = datetime.now(timezone.utc)
    patterns = [
        (r'(\d+)\s*second', 'seconds'),
        (r'(\d+)\s*minute', 'minutes'),
        (r'(\d+)\s*hour',   'hours'),
        (r'(\d+)\s*day',    'days'),
        (r'(\d+)\s*week',   'weeks'),
        (r'(\d+)\s*month',  'months'),
        (r'(\d+)\s*year',   'years'),
    ]
    for pattern, unit in patterns:
        m = re.search(pattern, text)
        if m:
            n = int(m.group(1))
            if unit == 'seconds': return now - timedelta(seconds=n)
            if unit == 'minutes': return now - timedelta(minutes=n)
            if unit == 'hours':   return now - timedelta(hours=n)
            if unit == 'days':    return now - timedelta(days=n)
            if unit == 'weeks':   return now - timedelta(weeks=n)
            if unit == 'months':  return now - timedelta(days=n*30)
            if unit == 'years':   return now - timedelta(days=n*365)
    return None


# ================================================================
#  DATE + VIEW FETCH — Scrapes channel page directly
#  Works from all regions. One HTTP request per channel.
#  RSS is geo-blocked in Pakistan so this is the reliable method.
# ================================================================
def get_channel_dates_and_views(channel_id, channel_url, vid_count):
    try:
        url     = f"https://www.youtube.com/channel/{channel_id}/videos"
        headers = {
            "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code != 200:
            return None, None, 0, 0

        page = resp.text

        # Extract relative dates and views from page
        time_texts = re.findall(
            r'"publishedTimeText":\{"simpleText":"([^"]+)"', page
        )
        view_texts = re.findall(
            r'"viewCountText":\{"simpleText":"([^"]+)"', page
        )

        if not time_texts:
            return None, None, 0, 0

        now        = datetime.now(timezone.utc)
        dates      = []
        views_list = []

        for t in time_texts[:30]:
            d = parse_relative_date(t)
            if d:
                dates.append(d)

        for v in view_texts[:30]:
            try:
                num = int(re.sub(r'[^\d]', '', v))
                if num > 0:
                    views_list.append(num)
            except Exception:
                pass

        if not dates:
            return None, None, 0, 0

        last_date   = max(dates)
        oldest_date = min(dates)
        oldest_days = (now - oldest_date).days

        # Better age estimation:
        # If oldest fetched video is "1 month ago" but channel has 20 videos,
        # and we fetched 15 — extrapolate proportionally
        fetched  = len(dates)
        if vid_count > fetched and fetched > 0:
            age_days = int(oldest_days * vid_count / fetched)
        else:
            age_days = oldest_days

        # Estimate total views from avg of recent videos
        total_views = 0
        if views_list and vid_count > 0:
            avg_v       = sum(views_list) / len(views_list)
            total_views = int(avg_v * vid_count)

        # Recent views = views of most recent video (index 0 = newest)
        recent_views = views_list[0] if views_list else 0

        return last_date, age_days, total_views, recent_views

    except Exception:
        return None, None, 0, 0


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
                            faceless_score, recent_views=0):
    score = 0
    vpv   = view_count / max(vid_count, 1) if vid_count > 0 else 0

    # ── 1. AGE + VPV COMBINED — the core signal (max 45) ─────────
    if age_days is not None:
        if age_days <= 90:
            if vpv >= 200000:   score += 45
            elif vpv >= 100000: score += 40
            elif vpv >= 50000:  score += 35
            elif vpv >= 20000:  score += 28
            elif vpv >= 5000:   score += 18
            elif vpv >= 1000:   score += 8
        elif age_days <= 180:
            if vpv >= 500000:   score += 40
            elif vpv >= 200000: score += 33
            elif vpv >= 100000: score += 26
            elif vpv >= 50000:  score += 18
            elif vpv >= 20000:  score += 10
            elif vpv >= 5000:   score += 4
        elif age_days <= 365:
            if vpv >= 500000:   score += 30
            elif vpv >= 200000: score += 20
            elif vpv >= 100000: score += 12
            elif vpv >= 50000:  score += 5
    else:
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

    # ── 4. Recent activity (max 15) ──────────────────────────────
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

    # ── 6. RECENT VIRAL SIGNAL (max 15) ──────────────────────────
    # Recent video getting good views = audience loves the content
    # Last 30 days checked (not just 7) to allow upload schedule variation
    if recent_views > 0 and last_video_days is not None and last_video_days <= 30:
        if recent_views >= 200000:   score += 15
        elif recent_views >= 100000: score += 12
        elif recent_views >= 50000:  score += 10
        elif recent_views >= 30000:  score += 7
        elif recent_views >= 10000:  score += 4
        elif recent_views >= 3000:   score += 2

    # ── 7. SWEET SPOT BONUS (max 10) ─────────────────────────────
    # Core golden pattern: young channel, quality content, fast growth
    # Slightly loose ranges to allow natural variation
    # ~2-5 months old + decent subs + not spamming videos
    if (age_days is not None and 60 <= age_days <= 180
            and subs >= 15000
            and 8 <= vid_count <= 40):
        score += 10
    # Partial bonus — meets most but not all conditions
    elif (age_days is not None and 60 <= age_days <= 180
            and subs >= 8000
            and 8 <= vid_count <= 40):
        score += 5

    return min(score, 100)


# ================================================================
#  CHANNEL SCORER
# ================================================================
# INTELLIGENT NICHE THRESHOLD SYSTEM
# Adjusts golden score threshold per niche based on existing data.
# Stays within ±5 points of your personal GOLDEN_SCORE_MIN setting.
# Never goes too loose (bad results) or too tight (zero results).
# ================================================================
def get_niche_threshold(conn, niche):
    try:
        c = conn.cursor()
        # Get score distribution for this niche
        c.execute('''SELECT AVG(golden_score), MAX(golden_score), COUNT(*)
                     FROM channels WHERE niche=?''', (niche,))
        row = c.fetchone()
        if not row or not row[0] or row[2] < 10:
            # Not enough data yet — use your personal threshold
            return GOLDEN_SCORE_MIN

        avg_score = row[0]
        max_score = row[1]
        count     = row[2]

        # Calculate intelligent threshold:
        # If average score is very low, loosen slightly (but max -5)
        # If average score is high, tighten slightly (but max +5)
        # Always anchored to your personal GOLDEN_SCORE_MIN
        if avg_score < 20:
            # Very low scoring niche — loosen by up to 5 points
            adjustment = -min(5, int((20 - avg_score) / 4))
        elif avg_score > 50:
            # High scoring niche — tighten by up to 3 points
            adjustment = min(3, int((avg_score - 50) / 5))
        else:
            adjustment = 0

        threshold = GOLDEN_SCORE_MIN + adjustment

        # Hard boundaries: never below 45 or above 65
        threshold = max(45, min(65, threshold))
        return threshold
    except Exception:
        return GOLDEN_SCORE_MIN


# ================================================================
def score_channel(channel, niche, conn=None):
    now = datetime.now(timezone.utc)

    try:
        # ── yt-dlp scraping ───────────────────────────────────────
        real_cid = channel.get("channel_id", "")
        url_match = re.search(r"channel/(UC[A-Za-z0-9_-]{20,})", channel["channel_url"])
        if url_match:
            real_cid = url_match.group(1)

        if True:
            # ── yt-dlp scraping ───────────────────────────────────
            ydl_flat = {
                "quiet": True, "no_warnings": True,
                "extract_flat": True, "playlistend": 1,
                "ignoreerrors": True,
            }
            with yt_dlp.YoutubeDL(ydl_flat) as ydl:
                info = ydl.extract_info(channel["channel_url"], download=False)

            subs      = info.get("channel_follower_count") or 0
            vid_count = info.get("playlist_count") or 0
            name      = info.get("channel") or channel["channel_name"]
            desc      = info.get("description") or ""
            language  = info.get("language") or ""
            view_count = info.get("view_count") or 0
            video_titles = []
            avg_duration = 0
            uploads_pm   = 0.0
            avg_engage   = 0.0

            # Extract real UCxxxx ID
            if not real_cid or not real_cid.startswith("UC"):
                real_cid = info.get("channel_id") or ""
            if not real_cid or not real_cid.startswith("UC"):
                info_url = info.get("channel_url") or ""
                m = re.search(r"channel/(UC[A-Za-z0-9_-]{20,})", info_url)
                if m:
                    real_cid = m.group(1)
            if not real_cid or not real_cid.startswith("UC"):
                uploader_id = info.get("uploader_id") or ""
                if uploader_id.startswith("UC"):
                    real_cid = uploader_id
            if not real_cid:
                real_cid = channel["channel_id"]

            # English filter for scraping fallback
            if language and language not in ("en", "en-US", "en-GB",
                                              "en-AU", "en-CA", "en-IN", "", None):
                return None

            # Get dates via page scrape
            last_date, age_days, ytdlp_views, recent_views = get_channel_dates_and_views(
                real_cid, channel["channel_url"], vid_count
            )
            last_video_days = None
            if last_date is not None:
                last_video_days = (now - last_date).days
            if view_count == 0 and ytdlp_views > 0:
                view_count = ytdlp_views

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

        # ── FILTERS ──────────────────────────────────────────────────
        # Reject zero-data channels
        if subs == 0 and vid_count == 0:
            return None

        # Subscribers must be between 10K and 50K
        if subs > 50000:
            return None
        if subs < 10000:
            return None

        # Videos must be less than 50
        if vid_count >= 50:
            return None

        # Channel must be at least 4 months old (120 days)
        if age_days is not None and age_days < 120:
            return None

        # Reject clearly foreign script channels
        def foreign_script_ratio(text):
            if not text: return 0.0
            letter_count = foreign_count = 0
            for ch in text:
                cp = ord(ch)
                if cp < 128:
                    if ch.isalpha(): letter_count += 1
                    continue
                if (0x0600<=cp<=0x06FF or 0x0900<=cp<=0x097F or
                    0x0980<=cp<=0x09FF or 0x4E00<=cp<=0x9FFF or
                    0x3040<=cp<=0x30FF or 0xAC00<=cp<=0xD7AF or
                    0x0400<=cp<=0x04FF or 0x0E00<=cp<=0x0E7F):
                    foreign_count += 1; letter_count += 1
            return foreign_count / letter_count if letter_count else 0.0
        if foreign_script_ratio(name) > 0.25 or foreign_script_ratio(desc[:300]) > 0.40:
            return None

        # ── FACELESS DETECTION — score only, no hard reject ──────────
        # We score faceless confidence but do NOT reject based on it
        # User manually reviews all channels in dashboard and decides
        try:
            is_faceless, faceless_score = detect_faceless_full(
                channel_name=name,
                description=desc,
                video_titles=video_titles,
            )
        except Exception:
            is_faceless, faceless_score = False, 0

        # ── SCORING ───────────────────────────────────────────────────
        golden_score    = calculate_golden_score(
            subs, vid_count, view_count,
            age_days, last_video_days,
            faceless_score, recent_views
        )
        niche_threshold = get_niche_threshold(conn, niche) if conn else GOLDEN_SCORE_MIN

        return {
            "channel_id":         real_cid,
            "channel_name":       name,
            "channel_url":        f"https://www.youtube.com/channel/{real_cid}",
            "niche":              niche,
            "subscribers":        subs,
            "total_views":        view_count,
            "video_count":        vid_count,
            "discovered_via":     channel["discovered_via"],
            "golden_score":       golden_score,
            "is_golden":          1 if golden_score >= niche_threshold else 0,
            "is_faceless":        1 if is_faceless else 0,
            "faceless_score":     faceless_score,
            "channel_age_days":   age_days,
            "last_video_days":    last_video_days,
            "recent_views":       recent_views,
            "description":        desc[:500] if desc else "",
            "channel_handle":     channel.get("handle", ""),
            "date_found":         now.isoformat(),
            "review_status":      "pending",
        }

    except Exception as e:
        import traceback
        print(f"  [ERR] score_channel failed: {e}")
        traceback.print_exc()
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
        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
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
        ch.get("review_status", "pending"),
        ch.get("recent_views", 0),
        ch.get("description", ""),
        ch.get("channel_handle", ""),
    ))
    conn.commit()


# ================================================================
#  PRINT STATUS
# ================================================================
def print_status(ch):
    score        = ch["golden_score"]
    subs         = ch["subscribers"]
    name         = ch["channel_name"]
    niche        = ch.get("niche", "")
    age          = ch.get("channel_age_days")
    last         = ch.get("last_video_days")
    vid_count    = ch.get("video_count") or 0
    total_views  = ch.get("total_views") or 0
    faceless_sc  = ch.get("faceless_score") or 0
    recent_views = ch.get("recent_views") or 0

    age_str  = f"{age}d"  if age  is not None else "?"
    last_str = f"{last}d" if last is not None else "?"

    # Format subs
    if subs >= 1000000:
        subs_str = f"{subs/1000000:.1f}M"
    elif subs >= 1000:
        subs_str = f"{subs/1000:.1f}K"
    else:
        subs_str = str(subs)

    # VPV
    vpv = int(total_views / max(vid_count, 1)) if vid_count > 0 else 0
    if vpv >= 1000000:
        vpv_str = f"{vpv/1000000:.1f}M"
    elif vpv >= 1000:
        vpv_str = f"{vpv/1000:.0f}K"
    else:
        vpv_str = str(vpv) if vpv > 0 else "—"

    # Recent views
    if recent_views >= 1000000:
        rv_str = f"{recent_views/1000000:.1f}M"
    elif recent_views >= 1000:
        rv_str = f"{recent_views/1000:.0f}K"
    else:
        rv_str = str(recent_views) if recent_views > 0 else "—"

    # Consistent views signal
    consistent = "YES" if recent_views >= 10000 else "no"

    # Faceless label
    if faceless_sc >= 70:
        face_str = "FACELESS✓"
    elif faceless_sc >= 40:
        face_str = "likely"
    else:
        face_str = "unclear"

    # Status tag
    if score >= GOLDEN_SCORE_MIN:
        tag   = "★ GOLDEN"
        line  = "=" * 72
        print(f"\n  {line}")
        print(f"  {tag}  ┃  Score: {score}/100  ┃  {name}")
        print(f"  {line}")
    elif score >= PROMISING_SCORE_MIN:
        tag = "▲ PROMISING"
        print(f"\n  {'─'*72}")
        print(f"  {tag}  ┃  Score: {score}/100  ┃  {name}")
    else:
        # Regular — compact single line
        print(f"     regular  {score:>3}/100 | {name:<32} | "
              f"Age:{age_str:>5} Last:{last_str:>4} Subs:{subs_str:>7}")
        return

    # Detailed block for Golden and Promising only
    print(f"  {'─'*72}")
    print(f"  Niche          : {niche}")
    print(f"  Channel Age    : {age_str}  (started ~{age_str} ago)")
    print(f"  Last Upload    : {last_str} ago")
    print(f"  Total Videos   : {vid_count}")
    print(f"  Subscribers    : {subs_str}")
    print(f"  Views/Video    : {vpv_str}")
    print(f"  Latest Video   : {rv_str} views")
    print(f"  Consistent?    : {consistent}  (latest vid {rv_str})")
    print(f"  Faceless       : {face_str}  ({faceless_sc}%)")
    print(f"  {'─'*72}")


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
def run_niche(conn, niche):
    """Run full discovery for a single niche. Returns count of channels found."""
    save_niche(conn, niche)
    keywords = load_keywords(conn, niche)

    if not keywords:
        print(f"  Generating keywords for {niche.upper()}...")
        try:
            subtopics = generate_keywords(niche)
            saved     = save_keywords(conn, niche, subtopics)
            print(f"  {saved} keywords generated.")
            keywords  = load_keywords(conn, niche)
        except (json.JSONDecodeError, requests.HTTPError) as e:
            print(f"  Keyword generation failed: {e}")
            return 0
    else:
        print(f"  {len(keywords)} keywords ready.")

    total_kw    = len(keywords)
    all_found   = {}
    found_count = 0

    for idx, (keyword, subtopic) in enumerate(keywords, 1):
        print(f"\n  [{idx}/{total_kw}] {keyword}")

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
                ex.submit(score_channel, ch, niche, conn): cid
                for cid, ch in new_channels.items()
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result is None:
                        continue
                    save_channel(conn, result)
                    print_status(result)
                    found_count += 1
                except Exception:
                    pass

        mark_searched(conn, keyword, niche)
        time.sleep(0.3)

    return found_count


def main():
    import sys
    conn = init_db()

    # ── MODE: custom niche passed as argument ──────────────────────
    if len(sys.argv) > 1 and sys.argv[1] == "--custom":
        custom = " ".join(sys.argv[2:]).strip().lower()
        if not custom:
            custom = input("  Type your custom niche: ").strip().lower()
        niches_to_run = [custom]
        print(f"\n  Custom niche: {custom.upper()}")

    # ── MODE: single niche from menu ──────────────────────────────
    elif len(sys.argv) > 1 and sys.argv[1] == "--pick":
        niche = show_niche_menu()
        niches_to_run = [niche]

    # ── MODE: all niches automatically ───────────────────────────
    else:
        all_niches_flat = [n for cat in ALL_NICHES.values() for n in cat]
        niches_to_run   = all_niches_flat
        print(f"\n  AUTO MODE — Running all {len(niches_to_run)} niches")
        print(f"  No prompts. All channels saved for manual review.")
        print(f"  Press Ctrl+C at any time to stop.\n")

    print(f"\n  Settings:")
    print(f"    Results/keyword  : {RESULTS_PER_KEYWORD}")
    print(f"    Parallel workers : {PARALLEL_WORKERS}")
    print(f"    Age filter       : max {MAX_CHANNEL_AGE_DAYS} days")
    print(f"    Activity filter  : last video max {MAX_LAST_VIDEO_DAYS} days")
    print(f"    Scoring only     : no faceless hard reject")
    print(f"\n{'='*70}\n")

    total_found = 0
    for i, niche in enumerate(niches_to_run, 1):
        print(f"\n{'='*70}")
        print(f"  NICHE [{i}/{len(niches_to_run)}] — {niche.upper()}")
        print(f"{'='*70}")
        count = run_niche(conn, niche)
        total_found += count
        print(f"\n  Niche complete — {count} channels saved")

    print(f"\n{'='*70}")
    print(f"  ALL DONE")
    print(f"{'='*70}")
    print(f"  Total channels saved : {total_found}")
    print(f"  Now open Manual Review to approve golden channels.")

    show_summary(conn)
    conn.close()

    # ── Auto-sync to Supabase if configured ───────────────────────
    try:
        from supabase_sync import sync_to_supabase
        sync_to_supabase(verbose=True)
    except Exception as e:
        print(f"  [SYNC] Cloud sync skipped: {e}")


if __name__ == "__main__":
    main()
