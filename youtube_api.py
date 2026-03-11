# ================================================================
#  YOUTUBE API — Official Data API v3
#  Replaces all yt-dlp scraping with clean accurate data
#
#  What this fixes vs old scraping:
#  - Channel names no longer contain "1.6M views 3 hours ago" junk
#  - Subscriber counts are exact not estimated
#  - Channel creation date is exact ISO timestamp not guessed
#  - Video counts are accurate not 0 due to parsing failures
#  - Works from Pakistan and all regions (no geo-blocking)
#  - Engagement data (likes, comments) now available
#  - Video duration now available
#
#  Quota usage (free tier = 10,000 units/day):
#  - search.list          = 100 units per call
#  - channels.list        = 1 unit per call
#  - playlistItems.list   = 1 unit per call
#  - videos.list          = 1 unit per call
#
#  Typical discovery run (259 keywords):
#  - 259 searches × 100 = 25,900 units (3 days quota)
#  - To stay within 1 day: reduce RESULTS_PER_KEYWORD to 5
#    or use yt-dlp for search + API only for channel detail
#
#  RECOMMENDED HYBRID MODE (default):
#  - yt-dlp handles search (free, no quota)
#  - API handles channel detail (1 unit per channel)
#  This gives best of both worlds
# ================================================================

import re
import requests
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()
YT_API_KEY = os.getenv("YOUTUBE_API_KEY")

BASE_URL = "https://www.googleapis.com/youtube/v3"


# ================================================================
#  QUOTA TRACKER — Tracks daily API usage
# ================================================================
_quota_used = 0
QUOTA_LIMIT = 9000   # Leave 1000 buffer from 10000 daily limit

def quota_used():
    return _quota_used

def quota_remaining():
    return QUOTA_LIMIT - _quota_used

def _charge_quota(units):
    global _quota_used
    _quota_used += units
    if _quota_used >= QUOTA_LIMIT:
        print(f"\n  ⚠️  QUOTA WARNING: {_quota_used}/{QUOTA_LIMIT} units used today.")
        print("  Discovery will switch to scraping fallback for remaining channels.")


# ================================================================
#  SEARCH — Find channels by keyword
#  Cost: 100 units per call
#  Use yt-dlp for search to save quota — only call this if needed
# ================================================================
def search_channels_api(keyword: str, max_results: int = 10) -> list:
    """
    Search YouTube for channels matching keyword.
    Returns list of channel_id strings.
    Cost: 100 quota units per call.
    """
    if not YT_API_KEY:
        return []
    if quota_remaining() < 100:
        return []

    try:
        resp = requests.get(f"{BASE_URL}/search", params={
            "key":              YT_API_KEY,
            "q":                keyword,
            "type":             "channel",
            "part":             "snippet",
            "maxResults":       max_results,
            "relevanceLanguage": "en",
            "regionCode":       "US",
        }, timeout=10)

        _charge_quota(100)

        if resp.status_code != 200:
            return []

        data  = resp.json()
        items = data.get("items") or []
        return [
            item["snippet"]["channelId"]
            for item in items
            if item.get("snippet", {}).get("channelId")
        ]
    except Exception:
        return []


# ================================================================
#  CHANNEL DETAIL — Get full channel metadata
#  Cost: 1 unit per call
#  This is the main replacement for page scraping
# ================================================================
def get_channel_detail(channel_id: str) -> dict | None:
    """
    Get complete channel metadata from YouTube API.
    Returns clean dict with all fields needed for scoring.
    Cost: 1 quota unit.

    Replaces:
    - get_channel_dates_and_views() scraping
    - The junk channel name parsing bug
    - 0-subscriber filter bypass
    - None age scoring bug
    """
    if not YT_API_KEY:
        return None
    if quota_remaining() < 1:
        return None

    try:
        resp = requests.get(f"{BASE_URL}/channels", params={
            "key":  YT_API_KEY,
            "id":   channel_id,
            "part": "snippet,statistics,contentDetails",
        }, timeout=10)

        _charge_quota(1)

        if resp.status_code != 200:
            return None

        data  = resp.json()
        items = data.get("items") or []
        if not items:
            return None

        item       = items[0]
        snippet    = item.get("snippet",    {})
        stats      = item.get("statistics", {})
        content    = item.get("contentDetails", {})

        # ── Parse exact channel creation date ────────────────────
        created_at = snippet.get("publishedAt")   # ISO: "2023-11-15T10:22:00Z"
        now        = datetime.now(timezone.utc)
        age_days   = None

        if created_at:
            try:
                created_dt = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
                age_days = (now - created_dt).days
            except Exception:
                pass

        # ── Clean statistics ──────────────────────────────────────
        subs        = int(stats.get("subscriberCount", 0) or 0)
        total_views = int(stats.get("viewCount",       0) or 0)
        vid_count   = int(stats.get("videoCount",      0) or 0)

        # ── Uploads playlist ID (for fetching recent videos) ─────
        uploads_playlist = (
            content.get("relatedPlaylists", {}).get("uploads") or ""
        )

        return {
            "channel_id":        channel_id,
            "channel_name":      snippet.get("title", "Unknown"),   # Clean name only
            "description":       snippet.get("description", ""),
            "country":           snippet.get("country", ""),
            "created_at":        created_at,
            "age_days":          age_days,
            "subscribers":       subs,
            "total_views":       total_views,
            "video_count":       vid_count,
            "uploads_playlist":  uploads_playlist,
        }

    except Exception:
        return None


# ================================================================
#  RECENT VIDEOS — Get latest video metadata
#  Cost: 1 unit per call (playlistItems) + 1 unit (videos detail)
#  Replaces: get_channel_dates_and_views() page scraping
# ================================================================
def get_recent_videos(uploads_playlist: str, max_results: int = 10) -> list:
    """
    Get recent video IDs and publish dates from uploads playlist.
    Cost: 1 quota unit.
    """
    if not YT_API_KEY or not uploads_playlist:
        return []
    if quota_remaining() < 1:
        return []

    try:
        resp = requests.get(f"{BASE_URL}/playlistItems", params={
            "key":        YT_API_KEY,
            "playlistId": uploads_playlist,
            "part":       "snippet",
            "maxResults": max_results,
        }, timeout=10)

        _charge_quota(1)

        if resp.status_code != 200:
            return []

        data  = resp.json()
        items = data.get("items") or []

        videos = []
        for item in items:
            snip = item.get("snippet", {})
            vid_id = snip.get("resourceId", {}).get("videoId")
            pub_at = snip.get("publishedAt")
            title  = snip.get("title", "")
            if vid_id:
                videos.append({
                    "video_id":     vid_id,
                    "published_at": pub_at,
                    "title":        title,
                })
        return videos

    except Exception:
        return []


def get_video_details(video_ids: list) -> list:
    """
    Get view counts, duration, likes, comments for video IDs.
    Cost: 1 quota unit per call (up to 50 IDs per call).
    """
    if not YT_API_KEY or not video_ids:
        return []
    if quota_remaining() < 1:
        return []

    try:
        resp = requests.get(f"{BASE_URL}/videos", params={
            "key":  YT_API_KEY,
            "id":   ",".join(video_ids[:50]),
            "part": "statistics,contentDetails",
        }, timeout=10)

        _charge_quota(1)

        if resp.status_code != 200:
            return []

        data  = resp.json()
        items = data.get("items") or []

        results = []
        for item in items:
            stats   = item.get("statistics",     {})
            content = item.get("contentDetails", {})

            # Parse ISO 8601 duration: PT10M15S → seconds
            duration_str = content.get("duration", "PT0S")
            duration_sec = _parse_duration(duration_str)

            results.append({
                "video_id":       item["id"],
                "views":          int(stats.get("viewCount",    0) or 0),
                "likes":          int(stats.get("likeCount",    0) or 0),
                "comments":       int(stats.get("commentCount", 0) or 0),
                "duration_secs":  duration_sec,
                "is_short":       1 if duration_sec < 61 else 0,
            })
        return results

    except Exception:
        return []


def _parse_duration(duration: str) -> int:
    """Parse ISO 8601 duration string to seconds. PT10M15S → 615"""
    if not duration:
        return 0
    hours   = re.search(r"(\d+)H", duration)
    minutes = re.search(r"(\d+)M", duration)
    seconds = re.search(r"(\d+)S", duration)
    total   = 0
    if hours:   total += int(hours.group(1))   * 3600
    if minutes: total += int(minutes.group(1)) * 60
    if seconds: total += int(seconds.group(1))
    return total


# ================================================================
#  MASTER FUNCTION — Full channel data in one call
#  This is what giant.py calls instead of scraping
#  Total cost: ~3-4 quota units per channel
# ================================================================
def get_full_channel_data(channel_id: str) -> dict | None:
    """
    Get everything needed to score a channel.
    Combines channel detail + recent video data + engagement.

    Returns enriched dict ready for calculate_golden_score().
    Falls back gracefully if API key missing or quota exceeded.
    """
    # ── Step 1: Channel metadata ──────────────────────────────────
    detail = get_channel_detail(channel_id)
    if not detail:
        return None

    # ── Step 2: Recent videos ─────────────────────────────────────
    now          = datetime.now(timezone.utc)
    last_video_days  = None
    recent_views     = 0
    avg_duration     = 0
    uploads_per_month = 0.0
    avg_engagement   = 0.0
    video_titles     = []

    uploads_pl = detail.get("uploads_playlist")
    if uploads_pl:
        recent = get_recent_videos(uploads_pl, max_results=15)

        if recent:
            # Most recent video publish date
            pub_at = recent[0].get("published_at")
            if pub_at:
                try:
                    pub_dt = datetime.fromisoformat(
                        pub_at.replace("Z", "+00:00")
                    )
                    last_video_days = (now - pub_dt).days
                except Exception:
                    pass

            # Collect titles for faceless detection
            video_titles = [v["title"] for v in recent if v.get("title")]

            # Get video stats (views, likes, duration)
            vid_ids = [v["video_id"] for v in recent if v.get("video_id")]
            if vid_ids:
                vid_details = get_video_details(vid_ids)

                if vid_details:
                    # Filter out Shorts for analysis
                    long_vids = [v for v in vid_details if not v["is_short"]]

                    if long_vids:
                        # Most recent video views
                        recent_views = long_vids[0]["views"] if long_vids else 0

                        # Average duration (long-form only)
                        avg_duration = int(
                            sum(v["duration_secs"] for v in long_vids)
                            / len(long_vids)
                        )

                        # Average engagement rate
                        total_views  = sum(v["views"]   for v in long_vids)
                        total_engage = sum(
                            v["likes"] + v["comments"] for v in long_vids
                        )
                        if total_views > 0:
                            avg_engagement = round(
                                total_engage / total_views * 100, 2
                            )

            # Upload frequency (videos per month based on recent activity)
            age_days = detail.get("age_days") or 0
            vid_count = detail.get("video_count") or 0
            if age_days > 0 and vid_count > 0:
                uploads_per_month = round((vid_count / age_days) * 30, 2)

    # ── Merge everything into one clean dict ──────────────────────
    return {
        # Core fields
        "channel_id":         channel_id,
        "channel_name":       detail["channel_name"],
        "description":        detail["description"],
        "channel_url":        f"https://www.youtube.com/channel/{channel_id}",
        "age_days":           detail["age_days"],
        "subscribers":        detail["subscribers"],
        "total_views":        detail["total_views"],
        "video_count":        detail["video_count"],

        # New enriched fields
        "last_video_days":    last_video_days,
        "recent_views":       recent_views,
        "avg_video_duration": avg_duration,
        "uploads_per_month":  uploads_per_month,
        "avg_engagement":     avg_engagement,
        "video_titles":       video_titles,

        # Quota info
        "quota_used":         quota_used(),
    }


# ================================================================
#  QUICK TEST — run directly to verify API key works
#  python youtube_api.py
# ================================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  YouTube API — Connection Test")
    print("="*60)

    if not YT_API_KEY:
        print("\n  ✗ YOUTUBE_API_KEY not found in .env file")
        print("  Add this line to your .env file:")
        print("  YOUTUBE_API_KEY=AIzaSy...")
        exit()

    print(f"\n  API Key found: {YT_API_KEY[:10]}...")
    print("\n  Testing with MrBeast channel (UCX6OQ3DkcsbYNE6H8uQQuVA)...")

    data = get_full_channel_data("UCX6OQ3DkcsbYNE6H8uQQuVA")
    if data:
        print(f"\n  ✓ API working correctly!")
        print(f"  Channel   : {data['channel_name']}")
        print(f"  Subs      : {data['subscribers']:,}")
        print(f"  Videos    : {data['video_count']}")
        print(f"  Age       : {data['age_days']} days")
        print(f"  Last video: {data['last_video_days']} days ago")
        print(f"  Avg views : {data['recent_views']:,}")
        print(f"  Avg dur   : {data['avg_video_duration']}s")
        print(f"  Engagement: {data['avg_engagement']}%")
        print(f"  Quota used: {data['quota_used']} units")
    else:
        print("\n  ✗ API call failed — check your API key")

    print("="*60 + "\n")
