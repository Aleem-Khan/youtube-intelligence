import requests
import re
from datetime import datetime, timezone, timedelta

def parse_relative_date(text):
    if not text:
        return None
    text = text.lower().strip()
    now = datetime.now(timezone.utc)
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

url = "https://www.youtube.com/channel/UC65iOHIfKDesHEJDgzNHZsg/videos"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

resp = requests.get(url, headers=headers, timeout=12)
text = resp.text

# Try multiple regex patterns
print("=== Testing regex patterns ===\n")

# Pattern 1
times1 = re.findall(r'"publishedTimeText":\{"simpleText":"([^"]+)"', text)
print(f"Pattern 1 results: {times1[:5]}")

# Pattern 2
times2 = re.findall(r'publishedTimeText["\s:]+simpleText["\s:]+([^"]+)"', text)
print(f"Pattern 2 results: {times2[:5]}")

# Pattern 3 - more flexible
times3 = re.findall(r'"publishedTimeText":\s*\{\s*"simpleText":\s*"([^"]+)"', text)
print(f"Pattern 3 results: {times3[:5]}")

# Pattern 4 - find raw occurrence and show surrounding context
idx = text.find("publishedTimeText")
if idx >= 0:
    print(f"\nRaw context around publishedTimeText:")
    print(repr(text[idx:idx+150]))

# viewCountText patterns
views1 = re.findall(r'"viewCountText":\{"simpleText":"([^"]+)"', text)
print(f"\nviewCountText pattern 1: {views1[:5]}")

idx2 = text.find("viewCountText")
if idx2 >= 0:
    print(f"\nRaw context around viewCountText:")
    print(repr(text[idx2:idx2+150]))
