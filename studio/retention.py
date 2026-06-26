"""Pull a video's retention curve from YouTube Analytics and save it next to
the episode for later review.

YouTube's Analytics API returns `videoViewRetention` as a list of
{elapsed_video_time_ratio, views} points — exactly the curve shown in YouTube
Studio's "Audience retention" report. We normalize the encoded "elapsed:ratio"
format into a plain ratio + views list.

Output: episodes/<slug>/retention.json with the curve + a flat .png chart.

CLI:
    python -m studio.retention episodes/<slug>
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from studio.config import load_settings
from studio.providers import youtube_data


@dataclass
class RetentionReport:
    """The full retention report shape written to disk."""
    video_id: str
    fetched_at: str
    start_date: str
    end_date: str
    duration_seconds: float
    curve: list[dict] = field(default_factory=list)
    # Summary stats computed from the curve
    avg_retention_pct: float = 0.0
    dropoff_at_30s_pct: float = 0.0
    dropoff_at_60s_pct: float = 0.0


def _read_video_id_and_duration(episode_dir: Path) -> tuple[str, float]:
    """Locate the youtube_video_id on state.json; get duration from the mp4
    (or fall back to 0 if ffprobe isn't available)."""
    state = json.loads((episode_dir / "state.json").read_text())
    video_id = state.get("youtube_video_id")
    if not video_id:
        raise ValueError(
            f"{episode_dir}/state.json has no youtube_video_id — was the video published?"
        )
    duration = 0.0
    mp4 = episode_dir / "video.mp4"
    if mp4.exists():
        import subprocess
        try:
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(mp4)],
                capture_output=True, text=True, check=True)
            duration = float(out.stdout.strip())
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            duration = 0.0
    return video_id, duration


def _build_summary(curve: list[dict], duration_seconds: float) -> dict:
    """Compute a few headline numbers from the raw curve."""
    if not curve:
        return {"avg_retention_pct": 0.0, "dropoff_at_30s_pct": 0.0,
                "dropoff_at_60s_pct": 0.0}
    peak = max(p["views"] for p in curve) or 1
    # Average retention: mean(views/peak) across the curve.
    avg = sum(p["views"] / peak for p in curve) / len(curve) * 100
    # Find the retention at (or just past) 30s and 60s.
    def _at(seconds: float) -> float:
        if duration_seconds <= 0:
            return 0.0
        target = seconds / duration_seconds
        # First point whose ratio >= target.
        for p in curve:
            if p["ratio"] >= target:
                return p["views"] / peak * 100
        return 0.0
    return {
        "avg_retention_pct": round(avg, 2),
        "dropoff_at_30s_pct": round(_at(30.0), 2),
        "dropoff_at_60s_pct": round(_at(60.0), 2),
    }


def build_report(curve: list[dict], *, video_id: str, start_date: str,
                 end_date: str, duration_seconds: float) -> RetentionReport:
    summary = _build_summary(curve, duration_seconds)
    return RetentionReport(
        video_id=video_id,
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        start_date=start_date,
        end_date=end_date,
        duration_seconds=duration_seconds,
        curve=curve,
        avg_retention_pct=summary["avg_retention_pct"],
        dropoff_at_30s_pct=summary["dropoff_at_30s_pct"],
        dropoff_at_60s_pct=summary["dropoff_at_60s_pct"],
    )


def write_report(report: RetentionReport, episode_dir: Path) -> Path:
    out = episode_dir / "retention.json"
    out.write_text(json.dumps(asdict(report), indent=2))
    return out


def _draw_chart(report: RetentionReport, episode_dir: Path) -> Path | None:
    """Render the curve to retention.png. matplotlib is optional — if it's
    not installed, skip silently. The JSON is the source of truth either way."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    if not report.curve or report.duration_seconds <= 0:
        return None
    xs = [p["ratio"] * report.duration_seconds for p in report.curve]
    ys = [p["views"] for p in report.curve]
    peak = max(ys) or 1
    ys_pct = [y / peak * 100 for y in ys]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(xs, ys_pct, color="#c47a2a", linewidth=1.5)
    ax.axhline(100, color="#888", linestyle="--", linewidth=0.5)
    ax.set_xlim(0, report.duration_seconds)
    ax.set_ylim(0, 105)
    ax.set_xlabel("seconds into video")
    ax.set_ylabel("audience retention (%)")
    ax.set_title(f"{report.video_id}  avg={report.avg_retention_pct:.1f}%  "
                 f"30s={report.dropoff_at_30s_pct:.1f}%  "
                 f"60s={report.dropoff_at_60s_pct:.1f}%")
    fig.tight_layout()
    out = episode_dir / "retention.png"
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="studio.retention",
        description="Pull a published video's retention curve into episodes/<slug>/.")
    parser.add_argument("episode_dir")
    parser.add_argument("--days", type=int, default=30,
        help="How many days back to query (default: 30)")
    parser.add_argument("--no-chart", action="store_true",
        help="Skip the retention.png render even if matplotlib is installed")
    args = parser.parse_args(argv)

    episode_dir = Path(args.episode_dir)
    settings = load_settings()

    video_id, duration = _read_video_id_and_duration(episode_dir)
    end = date.today()
    start = end - timedelta(days=args.days)

    creds = youtube_data.load_credentials_for_analytics(
        settings.youtube_client_secret, settings.youtube_token)
    token = creds.token
    raw = youtube_data.fetch_video_retention(
        token, video_id, start_date=start.isoformat(), end_date=end.isoformat())

    report = build_report(raw["curve"], video_id=video_id,
                          start_date=start.isoformat(), end_date=end.isoformat(),
                          duration_seconds=duration)
    out = write_report(report, episode_dir)
    print(f"wrote {out} ({len(report.curve)} points, "
          f"avg={report.avg_retention_pct:.1f}%)")

    if not args.no_chart:
        chart = _draw_chart(report, episode_dir)
        if chart:
            print(f"wrote {chart}")
    return 0


if __name__ == "__main__":
    sys.exit(main())