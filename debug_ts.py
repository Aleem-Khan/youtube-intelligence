import yt_dlp

url = "https://www.youtube.com/channel/UC65iOHIfKDesHEJDgzNHZsg/videos"

ydl_opts = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": "in_playlist",
    "playlistend": 3,
    "ignoreerrors": True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)

entries = [e for e in (info.get("entries") or []) if e]

for i, e in enumerate(entries[:3]):
    print(f"Video {i+1}:")
    print(f"  timestamp         : {e.get('timestamp')}")
    print(f"  release_timestamp : {e.get('release_timestamp')}")
    print(f"  upload_date       : {e.get('upload_date')}")
    print(f"  view_count        : {e.get('view_count')}")
