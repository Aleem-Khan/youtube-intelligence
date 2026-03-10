import yt_dlp

url = "https://www.youtube.com/channel/UC65iOHIfKDesHEJDgzNHZsg/videos"

ydl_opts = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": "in_playlist",
    "playlistend": 5,
    "ignoreerrors": True,
}

print(f"\nFetching: {url}\n")

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)

entries = [e for e in (info.get("entries") or []) if e]
print(f"Entries found: {len(entries)}\n")

for i, e in enumerate(entries[:3]):
    print(f"--- Video {i+1} ---")
    print(f"  title       : {e.get('title')}")
    print(f"  upload_date : {e.get('upload_date')}")
    print(f"  view_count  : {e.get('view_count')}")
    print(f"  duration    : {e.get('duration')}")
    print(f"  ALL KEYS    : {list(e.keys())}")
    print()
