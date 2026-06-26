"""Vertical 9:16 short-clip extractor for published Chariot of the Self episodes.

The main video pipeline produces a 16:9 episode. Most of its high-value moments
also work as standalone vertical shorts (TikTok / Reels / Shorts). This tool
picks the N most "short-worthy" passages from script.md and renders each one
as a 9:16 mp4 with burned-in captions and a tiny music bed.

What makes a passage short-worthy:
  - self-contained (one clear idea, doesn't depend on earlier context)
  - emotionally resonant (a vivid image or a quiet turn)
  - 45-75 seconds long (the sweet spot for Shorts retention)

The tool asks MiniMax chat to pick the passages, grounded in the script and
the channel voice. Pure functions split time-mapping from rendering so the
clip-selection logic can be tested without ffmpeg.

CLI:
    python -m studio.shorts episodes/<slug> --n 2
    python -m studio.shorts episodes/<slug> --n 2 --min-seconds 30 --max-seconds 90
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from studio.config import load_settings
from studio.providers import minimax


# Vertical 9:16 spec (Shorts / Reels / TikTok).
SHORT_W, SHORT_H = 1080, 1920
FPS = 25
# Default sweet spot for short-form retention.
DEFAULT_MIN_SECONDS = 45.0
DEFAULT_MAX_SECONDS = 75.0


# ----------------------------- data shapes ---------------------------------

@dataclass
class ScriptParagraph:
    """A self-contained chunk of the narration with its time window."""
    index: int
    text: str
    start_seconds: float
    end_seconds: float


@dataclass
class ShortPick:
    """One passage the LLM chose to turn into a short."""
    paragraph_index: int
    text: str
    start_seconds: float
    end_seconds: float
    rationale: str  # why the LLM picked it
    caption: str    # the burned-in caption text (often = a punchy first line)


@dataclass
class ShortsOutput:
    """The full output of one extract run — written to shorts.json."""
    slug: str
    source_video: str
    generated_at: str
    picks: list[ShortPick] = field(default_factory=list)
    rendered: list[str] = field(default_factory=list)  # paths to rendered mp4s


# --------------------------- script parsing -------------------------------

# Same word-counting as pipeline._script_beats so timing math lines up with
# the render pipeline (which sized each beat proportionally to its word count).
_NARRATION_IGNORED_PREFIXES = ("shot:", "clip:", "sfx:")


def parse_paragraphs(script_path: Path) -> list[ScriptParagraph]:
    """Split script.md into contiguous narration blocks. Each block is one
    paragraph: the lines that sit between two `Shot:`/`Clip:` markers (or
    the start/end of the file). SFX cues and bracketed stage directions are
    stripped.

    The "paragraph" boundary is what the LLM will choose between — it
    approximates the natural visual cuts in the body video.
    """
    paragraphs: list[list[str]] = [[]]
    for raw in script_path.read_text().splitlines():
        s = raw.strip()
        if not s:
            continue
        low = s.lower()
        if any(low.startswith(p) for p in _NARRATION_IGNORED_PREFIXES):
            paragraphs.append([])
            continue
        if s.startswith("[") and s.endswith("]"):
            continue  # stage direction
        if s.startswith("#"):
            continue  # markdown header
        paragraphs[-1].append(s)
    # Drop empty trailing paragraph.
    paras = [p for p in paragraphs if p]
    return [ScriptParagraph(index=i, text=" ".join(p), start_seconds=0.0,
                            end_seconds=0.0)
            for i, p in enumerate(paras)]


def time_paragraphs(paragraphs: list[ScriptParagraph], voiceover_seconds: float) -> list[ScriptParagraph]:
    """Assign time windows to each paragraph proportionally to its word count.
    Matches the render pipeline's per-beat timing math (see pipeline.py
    _script_beats + _build_hybrid_segments)."""
    counts = [max(1, len(p.text.split())) for p in paragraphs]
    total = sum(counts)
    cursor = 0.0
    out: list[ScriptParagraph] = []
    for p, c in zip(paragraphs, counts):
        dur = c / total * voiceover_seconds
        out.append(ScriptParagraph(index=p.index, text=p.text,
                                   start_seconds=cursor,
                                   end_seconds=cursor + dur))
        cursor += dur
    return out


def voiceover_seconds(episode_dir: Path) -> float:
    """Read the actual voiceover duration with ffprobe. Falls back to a
    re-computed estimate from the script if voiceover.wav is missing."""
    vo = episode_dir / "voiceover.wav"
    if vo.exists():
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(vo)],
            capture_output=True, text=True, check=True)
        return float(out.stdout.strip())
    # Estimate: ~155 wpm contemplative pacing -> ~2.58 wps.
    script = episode_dir / "script.md"
    if not script.exists():
        raise FileNotFoundError(f"{episode_dir} has neither voiceover.wav nor script.md")
    paras = parse_paragraphs(script)
    total_words = sum(max(1, len(p.text.split())) for p in paras)
    return total_words / 2.58


# --------------------------- LLM clip picker ------------------------------

_SYSTEM_PROMPT = """\
You are the short-form editor for "Chariot of the Self", a YouTube channel
that turns ancient Indian wisdom into practices for the modern mind.

You will be given the paragraphs of an episode's script, each with its
in-video time window. Pick the N most "Shorts-worthy" passages — the ones
most likely to be shared as standalone vertical clips on TikTok / Reels /
YouTube Shorts.

What makes a passage short-worthy:
1. SELF-CONTAINED — one clear idea, doesn't depend on earlier context.
   A viewer landing on it cold gets the whole point.
2. EMOTIONALLY RESONANT — a vivid image, a quiet turn, a surprise.
3. RIGHT LENGTH — between 45 and 75 seconds.

For each pick, also write a one-line BURNED-IN CAPTION (≤ 80 chars) that
captures the most quotable sentence or the strongest hook — this appears
on screen for the duration of the clip.

Output format (strict JSON, no prose around it):
{"picks": [
  {"paragraph_index": <int, matches the input>,
   "rationale": "one sentence on why this works as a short",
   "caption": "one line, ≤ 80 chars, burned on screen"}
]}

Output exactly N picks, no more, no less. Each paragraph_index MUST appear
at most once.\
"""


def _build_user_prompt(paragraphs: list[ScriptParagraph], n: int,
                       min_seconds: float, max_seconds: float) -> str:
    blocks = []
    for p in paragraphs:
        dur = p.end_seconds - p.start_seconds
        blocks.append(
            f"[paragraph {p.index} | {dur:.1f}s | "
            f"{p.start_seconds:.1f}s-{p.end_seconds:.1f}s]\n{p.text}\n"
        )
    body = "\n".join(blocks)
    return (
        f"Number of picks: {n}\n"
        f"Length window: {min_seconds:.0f}-{max_seconds:.0f} seconds\n\n"
        f"Paragraphs (with time windows):\n\n{body}\n\n"
        f"Pick the {n} most short-worthy passages. Each pick must fit the "
        f"length window and be self-contained."
    )


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


def _truncate_caption(text: str, max_chars: int = 80) -> str:
    """Keep the caption on one line, ≤ max_chars. Truncate on word boundary."""
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return (cut or text[:max_chars]).rstrip(",.;:-") + "…"


def pick_clips(settings, paragraphs: list[ScriptParagraph], *,
               n: int = 2, min_seconds: float = DEFAULT_MIN_SECONDS,
               max_seconds: float = DEFAULT_MAX_SECONDS) -> list[ShortPick]:
    """Ask the LLM which paragraphs to turn into shorts; cross-check each pick
    against the length window (drop ones that fall outside)."""
    msgs = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user",
         "content": _build_user_prompt(paragraphs, n, min_seconds, max_seconds)},
    ]
    url, headers, payload = minimax.chat_request(settings, msgs,
                                                  temperature=0.7, max_tokens=900)
    text = minimax.post_chat(url, headers, payload)
    parsed = _extract_json_object(text)
    raw_picks = parsed.get("picks") or []

    by_index = {p.index: p for p in paragraphs}
    out: list[ShortPick] = []
    seen: set[int] = set()
    for raw in raw_picks[:n]:
        idx = raw.get("paragraph_index")
        if not isinstance(idx, int) or idx in seen or idx not in by_index:
            continue
        para = by_index[idx]
        dur = para.end_seconds - para.start_seconds
        if dur < min_seconds or dur > max_seconds:
            continue
        out.append(ShortPick(
            paragraph_index=idx,
            text=para.text,
            start_seconds=para.start_seconds,
            end_seconds=para.end_seconds,
            rationale=(raw.get("rationale") or "").strip(),
            caption=_truncate_caption(raw.get("caption") or para.text),
        ))
        seen.add(idx)
    return out


# ----------------------------- caption render -----------------------------

_BRAND = Path(__file__).resolve().parents[1] / "brand"
_BOOKEND_MUSIC = _BRAND / "bookend-music.wav"


def _font(size: int) -> ImageFont.FreeTypeFont:
    """Same font fallback chain as studio.thumbnail."""
    for path in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_caption_overlay(caption: str, duration_seconds: float,
                           out_path: Path) -> Path:
    """Render a short-form caption as a single-frame PNG the size of the
    final short (1080x1920), with the caption centered horizontally near the
    upper third. The ffmpeg graph overlays this image on every frame.

    Keeping it as one PNG is simpler than re-encoding text via libass and
    matches the channel's flat, contemplative look. For animated captions
    (word-by-word) we'd move to ffmpeg's drawtext or a per-segment PNG
    sequence — out of scope for v1.
    """
    img = Image.new("RGB", (SHORT_W, SHORT_H), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Word-wrap manually to keep the caption inside ~80% of the width.
    max_w = int(SHORT_W * 0.86)
    font_size = 72
    lines: list[str] = []
    while font_size >= 36:
        font = _font(font_size)
        # Greedy wrap.
        words = caption.split()
        cur = ""
        wrapped: list[str] = []
        for w in words:
            test = (cur + " " + w).strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_w:
                cur = test
            else:
                if cur:
                    wrapped.append(cur)
                cur = w
        if cur:
            wrapped.append(cur)
        # Up to 3 lines; if more, we go smaller.
        if len(wrapped) <= 3:
            lines = wrapped
            break
        font_size -= 6
    font = _font(font_size)

    line_h = draw.textbbox((0, 0), "Ay", font=font)[3] + 8
    total_h = line_h * len(lines)
    # Position: upper third, vertically centered within that band.
    y0 = SHORT_H // 3 - total_h // 2

    # Drop shadow + cream fill, like the thumbnail text style.
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (SHORT_W - tw) // 2
        y = y0 + i * line_h
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0))  # shadow
        draw.text((x, y), line, font=font, fill=(240, 230, 210))     # cream

    img.save(out_path)
    return out_path


# ----------------------------- ffmpeg render ------------------------------

def render_short(pick: ShortPick, *, source_video: Path, out_path: Path,
                 caption_png: Path, music_path: Path | None) -> Path:
    """Render one short as a 9:16 mp4 with burned caption + tiny music bed.

    Input layout:
      [0:v/a] = source video + its voiceover audio
      [1:v/a] = music bed (optional; looped to fill)
      [2:v]   = caption PNG (looped as a still image)

    Filter graph (no music):
      [0:v] -> trim -> crop 9:16 center -> scale 1080x1920 -> [vsrc]
      [vsrc][2:v] overlay -> [vo]
      [0:a] -> atrim to clip window -> [va]
      [va] -> [aout]

    Filter graph (with music):
      [0:v] -> ... -> [vsrc]; [vsrc][2:v] overlay -> [vo]
      [0:a] -> atrim -> [va]
      [1:a] -> atrim + volume=0.05 + afade-out -> [vm]
      [va][vm] -> amix -> [aout]
    """
    duration = pick.end_seconds - pick.start_seconds
    # Crop centered: source is 1920x1080; we want 1080x1920 (a tall vertical
    # strip). crop takes (w:h:x:y) where x/y can be negative — ffmpeg pads.
    crop_w, crop_h = SHORT_W, 1920  # would need source >= 1920 tall
    # Since source is only 1080 tall, take the full height and widen the crop
    # horizontally (creating black bars is uglier than zooming in slightly).
    crop_w = 1920  # take the full source width
    crop_h = 1080
    # Then scale the 1920x1080 cropped region to 1080x1920 (vertical zoom).
    # This re-frames the video to fit the 9:16 canvas.
    crop_x = 0
    crop_y = 0

    # Build the input arg list — caption index depends on whether music is
    # included, so we track indices explicitly.
    inputs: list[str] = ["-i", str(source_video)]
    has_music = bool(music_path and Path(music_path).exists())
    if has_music:
        inputs += ["-stream_loop", "-1", "-i", str(music_path)]
        caption_idx = 2
        music_idx = 1
    else:
        caption_idx = 1
        music_idx = None
    inputs += ["-loop", "1", "-i", str(caption_png)]

    audio_mix_inputs = 2 if has_music else 1
    music_filter = ""
    if has_music:
        music_filter = (
            f";[{music_idx}:a]atrim=0:{duration:.3f},asetpts=PTS-STARTPTS,"
            f"volume=0.05,afade=t=out:st={max(0.0, duration - 1.5):.3f}:d=1.5[vm]"
        )

    filter_complex = (
        f"[0:v]trim={pick.start_seconds:.3f}:{pick.end_seconds:.3f},"
        f"setpts=PTS-STARTPTS,"
        f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},"
        # Scale to the short's 9:16 canvas; this zooms in because we keep the
        # full width but stretch the height by 1920/1080 = 1.78x.
        f"scale={SHORT_W}:{SHORT_H}:flags=lanczos[vsrc];"
        f"[vsrc][{caption_idx}:v]overlay=0:0:format=auto[vo];"
        f"[0:a]atrim={pick.start_seconds:.3f}:{pick.end_seconds:.3f},"
        f"asetpts=PTS-STARTPTS[va]"
        f"{music_filter};"
        f"{'[va][vm]' if has_music else '[va]'}"
        f"amix=inputs={audio_mix_inputs}:dropout_transition=0[aout]"
    )

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vo]", "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-shortest", str(out_path),
    ]
    subprocess.run(cmd, check=True)
    return out_path


# ----------------------------- top-level ----------------------------------

def extract(episode_dir: Path, *, n: int = 2, min_seconds: float = DEFAULT_MIN_SECONDS,
            max_seconds: float = DEFAULT_MAX_SECONDS,
            settings=None) -> ShortsOutput:
    """End-to-end: pick → render → write shorts.json + N mp4s in shorts/."""
    episode_dir = Path(episode_dir)
    settings = settings or load_settings()

    script_path = episode_dir / "script.md"
    video_path = episode_dir / "video.mp4"
    if not script_path.exists():
        raise FileNotFoundError(f"{script_path} not found")
    if not video_path.exists():
        raise FileNotFoundError(f"{video_path} not found — was the episode rendered?")

    duration = voiceover_seconds(episode_dir)
    paragraphs = time_paragraphs(parse_paragraphs(script_path), duration)
    picks = pick_clips(settings, paragraphs, n=n,
                       min_seconds=min_seconds, max_seconds=max_seconds)
    if not picks:
        raise RuntimeError(
            f"no passages fit the {min_seconds}-{max_seconds}s window — "
            f"try widening --min-seconds / --max-seconds"
        )

    shorts_dir = episode_dir / "shorts"
    shorts_dir.mkdir(exist_ok=True)

    out = ShortsOutput(
        slug=episode_dir.name,
        source_video=str(video_path),
        generated_at=__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(timespec="seconds"),
        picks=picks,
    )
    music_path = _BOOKEND_MUSIC if _BOOKEND_MUSIC.exists() else None
    for i, pick in enumerate(picks, 1):
        caption_png = shorts_dir / f"{i:02d}-caption.png"
        render_caption_overlay(pick.caption, pick.end_seconds - pick.start_seconds,
                               caption_png)
        mp4 = shorts_dir / f"{i:02d}.mp4"
        render_short(pick, source_video=video_path, out_path=mp4,
                     caption_png=caption_png, music_path=music_path)
        out.rendered.append(str(mp4))

    (episode_dir / "shorts.json").write_text(json.dumps(asdict(out), indent=2))
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="studio.shorts",
        description="Extract vertical 9:16 short clips from an episode.")
    parser.add_argument("episode_dir")
    parser.add_argument("-n", type=int, default=2,
        help="Number of shorts to extract (default: 2)")
    parser.add_argument("--min-seconds", type=float, default=DEFAULT_MIN_SECONDS,
        help=f"Min clip length in seconds (default: {DEFAULT_MIN_SECONDS:.0f})")
    parser.add_argument("--max-seconds", type=float, default=DEFAULT_MAX_SECONDS,
        help=f"Max clip length in seconds (default: {DEFAULT_MAX_SECONDS:.0f})")
    args = parser.parse_args(argv)

    out = extract(Path(args.episode_dir), n=args.n,
                  min_seconds=args.min_seconds, max_seconds=args.max_seconds)
    print(f"wrote {Path(args.episode_dir) / 'shorts.json'} "
          f"({len(out.rendered)} clips)")
    for path in out.rendered:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())