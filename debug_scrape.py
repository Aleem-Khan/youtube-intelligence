import requests
import re
import json
from datetime import datetime, timezone, timedelta

def parse_relative_date(text):
    """Convert '2 days ago', '3 weeks ago', '1 month ago' to datetime"""
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

def get_channel_dates_scrape(channel_id):
    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        print(f"Status: {resp.status_code}")

        # Extract ytInitialData JSON from page
        match = re.search(r'var ytInitialData\s*=\s*(\{.*?\});\s*</script>', resp.text, re.DOTALL)
        if not match:
            match = re.search(r'ytInitialData\s*=\s*(\{.*?\});', resp.text, re.DOTALL)
        if not match:
            print("ytInitialData not found in page")
            return

        data = json.loads(match.group(1))

        # Find publishedTimeText values
        text = json.dumps(data)
        times = re.findall(r'"publishedTimeText":\{"simpleText":"([^"]+)"', text)
        views = re.findall(r'"viewCountText":\{"simpleText":"([^"]+)"', text)

        print(f"\nFound {len(times)} publishedTimeText values:")
        for t in times[:5]:
            parsed = parse_relative_date(t)
            print(f"  '{t}' -> {parsed}")

        print(f"\nFound {len(views)} viewCountText values:")
        for v in views[:5]:
            print(f"  '{v}'")

    except Exception as e:
        print(f"Error: {e}")

get_channel_dates_scrape("UC65iOHIfKDesHEJDgzNHZsg")
