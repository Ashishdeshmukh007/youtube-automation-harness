"""Competitor research for the Chariot of the Self channel.

Given a niche keyword (or a list of seed channel handles), discover the
highest-performing channels in that niche and pull their top-view videos into
a JSON report. The report is the input to `/propose-topics` style ideation
and to the A/B title recommender.

The HTTP layer is in `studio.providers.youtube_data` so this module can be
exercised end-to-end with mocked responses.

CLI:
    python -m studio.competitors --query "bhagavad gita wisdom" \\
        --max-channels 10 --top-videos 5 \\
        --out competitor-reports/

    python -m studio.competitors --seed "@SchoolOfLife,@AnimatedGita" \\
        --max-videos 5 --out competitor-reports/
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from studio.config import load_settings
from studio.providers import youtube_data


@dataclass
class CompetitorVideo:
    id: str
    title: str
    viewCount: int
    likeCount: int
    commentCount: int
    publishedAt: str
    thumbnail_url: str


@dataclass
class CompetitorChannel:
    id: str
    title: str
    subscribers: int
    viewCount: int
    videoCount: int
    thumbnail_url: str
    top_videos: list[CompetitorVideo] = field(default_factory=list)


@dataclass
class CompetitorReport:
    """The full report shape. One JSON document per scan."""
    generated_at: str
    query: str | None
    seed_handles: list[str]
    channels: list[CompetitorChannel]


def _resolve_seed_handles(api_key: str, handles: list[str]) -> list[CompetitorChannel]:
    """Given a list of @handles, return stats for each (best-effort — skip ones
    that 404)."""
    channel_ids: list[str] = []
    handle_to_id: dict[str, str] = {}
    for h in handles:
        h = h.strip()
        if not h:
            continue
        try:
            cid = youtube_data.resolve_handle(api_key, h.lstrip("@"))
        except LookupError:
            print(f"[competitors] skip: handle @{h} not found", file=sys.stderr)
            continue
        channel_ids.append(cid)
        handle_to_id[h] = cid

    if not channel_ids:
        return []

    stats_by_id = {c["id"]: c for c in youtube_data.channel_stats_batch(api_key, channel_ids)}
    out: list[CompetitorChannel] = []
    for h, cid in handle_to_id.items():
        s = stats_by_id.get(cid)
        if not s:
            continue
        out.append(CompetitorChannel(
            id=s["id"], title=s["title"],
            subscribers=s["subscribers"], viewCount=s["viewCount"],
            videoCount=s["videoCount"], thumbnail_url=s["thumbnail_url"],
        ))
    return out


def _channels_from_query(api_key: str, query: str, *, max_channels: int) -> list[CompetitorChannel]:
    """Keyword search → top N channels by viewCount."""
    seeds = youtube_data.search_channels(api_key, query, max_results=max_channels)
    if not seeds:
        return []
    stats_by_id = {c["id"]: c for c in youtube_data.channel_stats_batch(
        api_key, [s["id"] for s in seeds])}
    out: list[CompetitorChannel] = []
    for s in seeds:
        st = stats_by_id.get(s["id"])
        if not st:
            continue
        out.append(CompetitorChannel(
            id=st["id"], title=st["title"],
            subscribers=st["subscribers"], viewCount=st["viewCount"],
            videoCount=st["videoCount"], thumbnail_url=st["thumbnail_url"],
        ))
    out.sort(key=lambda c: c.viewCount, reverse=True)
    return out


def attach_top_videos(api_key: str, channels: list[CompetitorChannel], *,
                      top_videos: int) -> None:
    """Mutates `channels` to attach each one's top-view videos. Pure side-effect
    on the passed-in list — separated so tests can call it after mocking."""
    for ch in channels:
        try:
            vids = youtube_data.top_videos_for_channel(api_key, ch.id, max_results=top_videos)
        except Exception as e:  # one bad channel shouldn't fail the whole scan
            print(f"[competitors] top-videos lookup failed for {ch.title}: {e}",
                  file=sys.stderr)
            continue
        ch.top_videos = [CompetitorVideo(**v) for v in vids]


def build_report(api_key: str, *, query: str | None,
                 seed_handles: list[str], max_channels: int,
                 top_videos: int) -> CompetitorReport:
    if not query and not seed_handles:
        raise ValueError("provide either --query or --seed")
    if query and seed_handles:
        raise ValueError("pass --query OR --seed, not both")

    if seed_handles:
        channels = _resolve_seed_handles(api_key, seed_handles)
    else:
        channels = _channels_from_query(api_key, query or "", max_channels=max_channels)  # type: ignore[arg-type]

    attach_top_videos(api_key, channels, top_videos=top_videos)

    return CompetitorReport(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        query=query,
        seed_handles=seed_handles,
        channels=channels,
    )


def write_report(report: CompetitorReport, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"competitors-{stamp}.json"
    out_path.write_text(json.dumps(asdict(report), indent=2))
    return out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="studio.competitors",
        description="Discover and rank competitor channels in your niche.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--query", help="Niche keyword (e.g. 'bhagavad gita wisdom')")
    src.add_argument("--seed", help="Comma-separated @handles (e.g. '@A,@B')")
    parser.add_argument("--max-channels", type=int, default=10,
        help="Max channels to discover from a keyword (default: 10)")
    parser.add_argument("--top-videos", type=int, default=5,
        help="Top videos per channel (default: 5)")
    parser.add_argument("--out", default="competitor-reports/",
        help="Output directory (default: competitor-reports/)")
    args = parser.parse_args(argv)

    settings = load_settings()
    api_key = settings.youtube_api_key
    if not api_key:
        print("error: YOUTUBE_API_KEY is not set in .env", file=sys.stderr)
        return 2

    seeds = [s.strip() for s in (args.seed or "").split(",") if s.strip()] if args.seed else []
    report = build_report(
        api_key,
        query=args.query, seed_handles=seeds,
        max_channels=args.max_channels, top_videos=args.top_videos,
    )
    out_path = write_report(report, Path(args.out))
    print(f"wrote {out_path} ({len(report.channels)} channels)")
    return 0


if __name__ == "__main__":
    sys.exit(main())