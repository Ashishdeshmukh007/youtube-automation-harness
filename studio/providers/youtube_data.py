"""Thin YouTube Data API v3 wrapper used by studio.competitors and
studio.retention. Public-data only — needs a server API key, NOT OAuth.

The API exposes everything we need for competitor research as GET requests on
youtube/v3. We avoid the google-api-python-client dependency to keep this
module pure HTTP and trivially mockable in tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode, urlparse, urlunparse

import requests

API_BASE = "https://www.googleapis.com/youtube/v3"


def _auth(api_key: str) -> dict:
    return {"Accept": "application/json"}


def _build_url(path: str, api_key: str, params: dict) -> str:
    """Append `key` to the query string and return the full URL."""
    merged = {**params, "key": api_key}
    parts = urlparse(f"{API_BASE}{path}")
    return urlunparse(parts._replace(query=urlencode(merged)))


def get_json(api_key: str, path: str, params: dict, *,
             timeout: int = 30) -> dict:
    """GET against the YouTube Data API; raise on non-2xx with the parsed body."""
    url = _build_url(path, api_key, params)
    resp = requests.get(url, headers=_auth(api_key), timeout=timeout)
    if resp.status_code >= 400:
        # YouTube returns structured error JSON; surface it for debugging.
        try:
            err = resp.json()
        except json.JSONDecodeError:
            err = {"raw": resp.text[:500]}
        raise RuntimeError(f"YouTube API {resp.status_code} on {path}: {err}")
    return resp.json()


def resolve_handle(api_key: str, handle: str) -> str:
    """Resolve a @handle to a channelId. Used to accept '@AnimatedGita' as input."""
    handle = handle.lstrip("@").strip()
    if not handle:
        raise ValueError("empty handle")
    body = get_json(api_key, "/channels", {"part": "id", "forHandle": f"@{handle}"})
    items = body.get("items") or []
    if not items:
        raise LookupError(f"channel not found for handle @{handle}")
    return items[0]["id"]


def search_channels(api_key: str, query: str, *, max_results: int = 10) -> list[dict]:
    """Find channels by keyword. Returns a list of {id, title, description}."""
    body = get_json(api_key, "/search", {
        "part": "snippet",
        "type": "channel",
        "q": query,
        "maxResults": min(max_results, 50),
        "order": "relevance",
    })
    out = []
    for it in body.get("items", []):
        sn = it.get("snippet", {})
        out.append({
            "id": it.get("id", {}).get("channelId") or sn.get("channelId") or "",
            "title": sn.get("title", ""),
            "description": sn.get("description", ""),
        })
    return [c for c in out if c["id"]]


def channel_stats(api_key: str, channel_id: str) -> dict:
    """Return {subscribers, viewCount, videoCount, title, thumbnail_url} for one channel."""
    body = get_json(api_key, "/channels", {
        "part": "statistics,snippet",
        "id": channel_id,
    })
    items = body.get("items") or []
    if not items:
        raise LookupError(f"channel not found: {channel_id}")
    item = items[0]
    stats = item.get("statistics", {})
    snip = item.get("snippet", {})
    thumbs = snip.get("thumbnails", {})
    thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {})
    return {
        "id": item["id"],
        "title": snip.get("title", ""),
        "subscribers": int(stats.get("subscriberCount", 0)),
        "viewCount": int(stats.get("viewCount", 0)),
        "videoCount": int(stats.get("videoCount", 0)),
        "thumbnail_url": thumb.get("url", ""),
    }


def channel_stats_batch(api_key: str, channel_ids: list[str]) -> list[dict]:
    """Look up stats for up to 50 channels in one call."""
    if not channel_ids:
        return []
    body = get_json(api_key, "/channels", {
        "part": "statistics,snippet",
        "id": ",".join(channel_ids[:50]),
    })
    out = []
    for item in body.get("items", []):
        stats = item.get("statistics", {})
        snip = item.get("snippet", {})
        thumbs = snip.get("thumbnails", {})
        thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {})
        out.append({
            "id": item["id"],
            "title": snip.get("title", ""),
            "subscribers": int(stats.get("subscriberCount", 0)),
            "viewCount": int(stats.get("viewCount", 0)),
            "videoCount": int(stats.get("videoCount", 0)),
            "thumbnail_url": thumb.get("url", ""),
        })
    return out


def top_videos_for_channel(api_key: str, channel_id: str, *, max_results: int = 5) -> list[dict]:
    """Return the channel's top-view videos as [{id, title, viewCount, likeCount,
    commentCount, publishedAt, thumbnail_url}]."""
    body = get_json(api_key, "/search", {
        "part": "snippet",
        "channelId": channel_id,
        "type": "video",
        "order": "viewCount",
        "maxResults": min(max_results, 50),
    })
    items = body.get("items") or []
    if not items:
        return []
    video_ids = [it["id"].get("videoId") for it in items if it.get("id", {}).get("videoId")]
    if not video_ids:
        return []
    stats_body = get_json(api_key, "/videos", {
        "part": "statistics,snippet",
        "id": ",".join(video_ids[:50]),
    })
    out = []
    for v in stats_body.get("items", []):
        s = v.get("statistics", {})
        sn = v.get("snippet", {})
        thumbs = sn.get("thumbnails", {})
        thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {})
        out.append({
            "id": v["id"],
            "title": sn.get("title", ""),
            "viewCount": int(s.get("viewCount", 0)),
            "likeCount": int(s.get("likeCount", 0)),
            "commentCount": int(s.get("commentCount", 0)),
            "publishedAt": sn.get("publishedAt", ""),
            "thumbnail_url": thumb.get("url", ""),
        })
    out.sort(key=lambda x: x["viewCount"], reverse=True)
    return out


# ----------------------------- Analytics API -----------------------------

ANALYTICS_BASE = "https://youtubeanalytics.googleapis.com/v2"


def analytics_get_json(access_token: str, path: str, params: dict, *,
                       timeout: int = 30) -> dict:
    """GET against YouTube Analytics API. Auth is an OAuth bearer token (different
    from the public Data API key) because retention data is owner-only."""
    url = f"{ANALYTICS_BASE}{path}?{urlencode({**params})}"
    resp = requests.get(url, headers={
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
    }, timeout=timeout)
    if resp.status_code >= 400:
        try:
            err = resp.json()
        except json.JSONDecodeError:
            err = {"raw": resp.text[:500]}
        raise RuntimeError(f"YouTube Analytics {resp.status_code} on {path}: {err}")
    return resp.json()


def fetch_video_retention(access_token: str, video_id: str, *,
                          start_date: str, end_date: str) -> dict:
    """Return the raw retention row for one video over [start_date, end_date].

    `start_date` / `end_date` are ISO 8601 dates (YYYY-MM-DD). The Analytics API
    treats the 'videoViewRetention' metric as a single row per (video, date
    range). Returns the parsed row, including the encoded 'elapsedVideoTimeRatio'
    curve as a list of {ratio, views} entries."""
    body = analytics_get_json(access_token, "/reports", {
        "ids": "channel==MINE",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "videoViewRetention",
        "filters": f"video=={video_id}",
        "dimensions": "elapsedVideoTimeRatio",
        "sort": "elapsedVideoTimeRatio",
    })
    rows = body.get("rows") or []
    if not rows:
        return {"video_id": video_id, "curve": []}
    # First column is the metric value (an int); second is the encoded ratio.
    curve = []
    for r in rows:
        # Retention rows: [views_at_elapsed_ratio, elapsedVideoTimeRatio]
        if len(r) < 2:
            continue
        # elapsedVideoTimeRatio is "elapsed:0.012345" — split it.
        elapsed = r[1]
        if isinstance(elapsed, str) and ":" in elapsed:
            _, ratio_str = elapsed.split(":", 1)
            try:
                ratio = float(ratio_str)
            except ValueError:
                continue
        else:
            try:
                ratio = float(elapsed)
            except (TypeError, ValueError):
                continue
        curve.append({"ratio": round(ratio, 6), "views": int(r[0])})
    return {"video_id": video_id, "curve": curve}


def load_credentials_for_analytics(client_secret: str, token: str):
    """Return google.oauth2 Credentials suitable for the Analytics API. Reuses
    the upload OAuth token (both are YouTube-scoped) — refreshes if needed."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if Path(token).exists():
        creds = Credentials.from_authorized_user_file(token, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(requests.Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
            creds = flow.run_local_server(port=0)
        Path(token).write_text(creds.to_json())
    return creds