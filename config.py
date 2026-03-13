import os
from dotenv import load_dotenv

load_dotenv()

# ================================================================
#  API KEYS  —  add all of these to your .env file
# ================================================================
GROQ_API_KEY    = os.getenv("GROQ_API_KEY")      # required
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")     # optional, fallback AI
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")    # optional, better channel data
SUPABASE_URL    = os.getenv("SUPABASE_URL")        # optional, cloud database
SUPABASE_KEY    = os.getenv("SUPABASE_KEY")        # optional, cloud database

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY missing from .env file")

# ================================================================
#  DATABASE
# ================================================================
DB_FILE = "intelligence.db"   # local SQLite — always used
# Supabase is optional cloud backup — system works fine without it

# ================================================================
#  AI MODELS
# ================================================================
# ── Groq (free, fast) ────────────────────────────────────────────
GROQ_MODEL        = "llama-3.3-70b-versatile"     # primary — best quality
GROQ_MODEL_FAST   = "llama-3.1-8b-instant"        # fallback — fastest
GROQ_MODEL_REASON = "deepseek-r1-distill-llama-70b"  # Phase 3+ reasoning

# ── Gemini (free, excellent) ──────────────────────────────────────
GEMINI_MODEL      = "gemini-2.0-flash"             # fallback when Groq quota hits
# Get free key at: https://aistudio.google.com

# ── AI priority order ────────────────────────────────────────────
# 1. Groq llama-3.3-70b-versatile   (primary)
# 2. Groq llama-3.1-8b-instant      (if quota hit)
# 3. Gemini 2.0 Flash               (if both Groq fail)
# System auto-switches — no manual action needed

# ================================================================
#  DISCOVERY SETTINGS
# ================================================================
RESULTS_PER_KEYWORD = 15
PARALLEL_WORKERS    = 3   # keep at 3 — higher values freeze PC

# ================================================================
#  SCORING THRESHOLDS
# ================================================================
GOLDEN_SCORE_MIN    = 50
PROMISING_SCORE_MIN = 30

# ================================================================
#  CHANNEL CRITERIA  (scoring reference only — NOT hard filters)
# ================================================================
MAX_SUBSCRIBERS      = 500000
MIN_SUBSCRIBERS      = 1000
MAX_CHANNEL_AGE_DAYS = 365
MAX_LAST_VIDEO_DAYS  = 40

