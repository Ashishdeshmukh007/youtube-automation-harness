"""A/B title recommender for Chariot of the Self episodes.

Reads an episode's current title from metadata.json, pulls a sample of
top-view videos in the same niche via YouTube Data API, and asks the MiniMax
chat model to recommend title variants grounded in the niche's winning
patterns and the channel's pain-first voice (see brand/brand-bible.md).

Output: episodes/<slug>/title-candidates.json with the variants and the
reasoning trace. The owner picks a winner; the choice becomes the new
metadata.title before publish.

CLI:
    python -m studio.title_recommend episodes/<slug> \\
        --niche "ancient indian wisdom anxiety"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from studio.config import load_settings
from studio.providers import minimax, youtube_data


@dataclass
class TitleCandidate:
    title: str
    rationale: str  # why the LLM suggested this variant
    template: str = ""  # which template it maps to (Stop X / [time] cure / etc.)


@dataclass
class TitleRecommendation:
    generated_at: str
    niche_query: str
    current_title: str
    top_titles_in_niche: list[dict]
    candidates: list[TitleCandidate] = field(default_factory=list)


# Prompt: ask the LLM for structured JSON output so we can parse it
# deterministically. The instructions encode the channel's voice + templates.
_SYSTEM_PROMPT = """\
You are the title writer for "Chariot of the Self", a YouTube channel that
turns ancient Indian wisdom (Bhagavad Gita, Upanishads, Yoga Sutras, Chanakya)
into practices for the modern mind. The channel is NOT religion — it's a
fellow-traveller voice that leads with the viewer's modern pain and earns
the click with a specific source second.

Title rules:
1. Lead with the modern pain or promise. The source comes second.
2. Keep titles to ~50-70 characters. Aim for ≤70 so YouTube doesn't truncate.
3. Use one of these proven templates (or a close variant):
   - "Stop [X] – [Y]'s most ignored lesson"
   - "The [time period] cure for [modern pain] ([source])"
   - "Why you [symptom] — and what [source] says"
4. Never use clickbait ("This ONE trick...", shocked faces, all-caps abuse).
5. Never use pure Sanskrit titles — no one searches for them.
6. The title must honestly reflect what the video teaches.

Output format (strict JSON, no prose around it):
{"candidates": [
  {"title": "...", "rationale": "one sentence on why this works",
   "template": "one of: stop_x | time_cure | why_symptom | other"}
]}

Output exactly N candidates, no more, no less.\
"""


def _load_metadata(episode_dir: Path) -> dict:
    meta_path = episode_dir / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"{meta_path} not found — has the script been written?")
    return json.loads(meta_path.read_text())


def fetch_niche_titles(api_key: str, niche_query: str, *,
                       max_results: int = 15) -> list[dict]:
    """Find top-view videos for the niche and return [{title, viewCount}]."""
    body = youtube_data.get_json(api_key, "/search", {
        "part": "snippet",
        "type": "video",
        "q": niche_query,
        "order": "viewCount",
        "maxResults": min(max_results, 50),
    })
    items = body.get("items") or []
    if not items:
        return []
    video_ids = [it["id"].get("videoId") for it in items if it.get("id", {}).get("videoId")]
    if not video_ids:
        return []
    stats = youtube_data.get_json(api_key, "/videos", {
        "part": "statistics,snippet",
        "id": ",".join(video_ids[:50]),
    })
    out = []
    for v in stats.get("items", []):
        s = v.get("statistics", {})
        sn = v.get("snippet", {})
        out.append({
            "title": sn.get("title", ""),
            "viewCount": int(s.get("viewCount", 0)),
        })
    out.sort(key=lambda x: x["viewCount"], reverse=True)
    return out


def _build_user_prompt(meta: dict, niche_titles: list[dict], n: int,
                       niche_query: str) -> str:
    sample = "\n".join(f"- {t['title']}  ({t['viewCount']:,} views)"
                       for t in niche_titles[:10])
    return (
        f"Niche query: {niche_query}\n\n"
        f"Current proposed title:\n  {meta.get('title', '(empty)')}\n\n"
        f"Current description (first 400 chars):\n"
        f"  {(meta.get('description', '') or '')[:400]}\n\n"
        f"Top-view titles already winning in this niche on YouTube:\n{sample}\n\n"
        f"Recommend {n} title variants for this episode that:\n"
        f"  - beat the current title on hook strength,\n"
        f"  - stay inside the channel voice (no clickbait, no pure Sanskrit),\n"
        f"  - are each ≤ 70 characters,\n"
        f"  - are differentiated from each other (don't give me 5 synonyms).\n"
    )


# Match a fenced ```json ... ``` block first; fall back to the first JSON
# object in the response. The LLM is supposed to return strict JSON, but
# occasional prose framing has slipped in during testing.
_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_JSON_ANY = re.compile(r"(\{.*\})", re.DOTALL)


def _extract_json_object(text: str) -> dict:
    m = _JSON_FENCE.search(text)
    candidate = m.group(1) if m else None
    if not candidate:
        m = _JSON_ANY.search(text)
        candidate = m.group(1) if m else None
    if not candidate:
        raise ValueError(f"could not find JSON object in chat response: {text[:200]}")
    return json.loads(candidate)


def build_recommendation(api_key: str, settings, meta: dict, niche_query: str,
                         *, n: int = 5, max_niche_titles: int = 15) -> TitleRecommendation:
    if api_key:
        niche_titles = fetch_niche_titles(api_key, niche_query,
                                          max_results=max_niche_titles)
    else:
        # Without an API key we still want the script to run — the LLM can
        # produce variants from the description alone. Surface a warning so
        # the owner knows they got a less-grounded recommendation.
        print("warning: YOUTUBE_API_KEY is empty — niche-titles sample will be empty. "
              "Set YOUTUBE_API_KEY for grounded recommendations.",
              file=sys.stderr)
        niche_titles = []

    msgs = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(meta, niche_titles, n, niche_query)},
    ]
    url, headers, payload = minimax.chat_request(settings, msgs,
                                                  temperature=0.8, max_tokens=900)
    text = minimax.post_chat(url, headers, payload)
    parsed = _extract_json_object(text)
    raw_candidates = parsed.get("candidates") or []

    return TitleRecommendation(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        niche_query=niche_query,
        current_title=meta.get("title", ""),
        top_titles_in_niche=niche_titles,
        candidates=[TitleCandidate(**c) for c in raw_candidates[:n]],
    )


def write_recommendation(rec: TitleRecommendation, episode_dir: Path) -> Path:
    out = episode_dir / "title-candidates.json"
    out.write_text(json.dumps(asdict(rec), indent=2))
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="studio.title_recommend",
        description="Recommend A/B title variants for an episode.")
    parser.add_argument("episode_dir")
    parser.add_argument("--niche", required=True,
        help="Search query describing the video's niche "
             "(e.g. 'ancient indian wisdom anxiety').")
    parser.add_argument("-n", type=int, default=5,
        help="Number of title variants to request (default: 5)")
    parser.add_argument("--max-niche-titles", type=int, default=15,
        help="How many top-view niche titles to sample for context "
             "(default: 15)")
    args = parser.parse_args(argv)

    episode_dir = Path(args.episode_dir)
    settings = load_settings()
    meta = _load_metadata(episode_dir)
    api_key = settings.youtube_api_key

    rec = build_recommendation(api_key, settings, meta, args.niche,
                                n=args.n, max_niche_titles=args.max_niche_titles)
    out = write_recommendation(rec, episode_dir)
    print(f"wrote {out} ({len(rec.candidates)} candidates)")
    for i, c in enumerate(rec.candidates, 1):
        print(f"  {i}. {c.title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())