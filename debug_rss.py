import requests
import re

cid = "UC65iOHIfKDesHEJDgzNHZsg"
rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

print(f"\nFetching: {rss_url}")
try:
    resp = requests.get(rss_url, headers=headers, timeout=12)
    print(f"Status code : {resp.status_code}")
    print(f"Response len: {len(resp.text)}")
    if resp.status_code == 200:
        dates = re.findall(r"<published>(\d{4}-\d{2}-\d{2})", resp.text)
        print(f"Dates found : {dates}")
        print(f"\nFirst 500 chars of response:\n{resp.text[:500]}")
    else:
        print(f"Response body: {resp.text[:300]}")
except Exception as e:
    print(f"ERROR: {e}")
