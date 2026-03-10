import requests
import re

url = "https://www.youtube.com/channel/UC65iOHIfKDesHEJDgzNHZsg/videos"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

resp = requests.get(url, headers=headers, timeout=12)
print(f"Status: {resp.status_code}")
print(f"Page size: {len(resp.text)} chars")
print(f"\n--- First 2000 chars ---")
print(resp.text[:2000])
print(f"\n--- Checking for key strings ---")
print(f"ytInitialData found : {'ytInitialData' in resp.text}")
print(f"publishedTimeText   : {'publishedTimeText' in resp.text}")
print(f"consentRequired     : {'consent' in resp.text.lower()}")
print(f"Sign in to confirm  : {'sign in' in resp.text.lower()}")
