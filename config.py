import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY in environment variables")

DB_FILE              = "intelligence.db"
GROQ_MODEL           = "llama-3.3-70b-versatile"

RESULTS_PER_KEYWORD  = 20
PARALLEL_WORKERS     = 5

GOLDEN_SCORE_MIN     = 55       # must score 55+ to be GOLDEN
MAX_SUBSCRIBERS      = 500000   # ignore giant channels
MIN_SUBSCRIBERS      = 1000     # ignore brand new empty channels
MAX_CHANNEL_AGE_DAYS = 365      # hard reject anything older than 1 year
MAX_LAST_VIDEO_DAYS  = 40       # hard reject inactive channels
