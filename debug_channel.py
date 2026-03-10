import yt_dlp
import re

# Test with Beeyond Ideas channel
TEST_URL = "https://www.youtube.com/@BeeyondIdeas"

print("\n=== SEARCH RESULT FIELDS ===")
ydl_opts = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": True,
    "playlist_items": "1-3",
    "ignoreerrors": True,
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    result = ydl.extract_info("ytsearch3:beeyond ideas space science", download=False)

for entry in (result.get("entries") or [])[:2]:
    if not entry:
        continue
    print(f"\n  channel        : {entry.get('channel')}")
    print(f"  channel_id     : {entry.get('channel_id')}")
    print(f"  channel_url    : {entry.get('channel_url')}")
    print(f"  uploader_id    : {entry.get('uploader_id')}")
    print(f"  uploader_url   : {entry.get('uploader_url')}")

print("\n=== CHANNEL PAGE FIELDS ===")
ydl_opts2 = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": True,
    "playlistend": 1,
    "ignoreerrors": True,
}
with yt_dlp.YoutubeDL(ydl_opts2) as ydl:
    info = ydl.extract_info(TEST_URL, download=False)

if info:
    print(f"\n  channel        : {info.get('channel')}")
    print(f"  channel_id     : {info.get('channel_id')}")
    print(f"  channel_url    : {info.get('channel_url')}")
    print(f"  uploader_id    : {info.get('uploader_id')}")
    print(f"  uploader_url   : {info.get('uploader_url')}")
    print(f"  id             : {info.get('id')}")

print("\nDone.")
