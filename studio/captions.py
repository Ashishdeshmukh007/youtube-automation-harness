"""Captions — produces an .srt sidecar from audio via Whisper, and (optionally)
burns captions into the source frames before assembly using PIL.

The ffmpeg `subtitles` filter requires libass which isn't available in the
homebrew build we use. So when burned-in captions are requested, the engine
renders each SRT line onto the corresponding frames as PNG text overlays,
and then the assembly step uses the overlaid frames instead of the originals.

Per-shot behavior: captions are NOT animated word-by-word (we'd need a real
subtitle renderer for that). Instead, each shot gets the static concatenation
of all caption text that overlaps its time slice. This is a tradeoff: less
fancy than real subs, but visible and legible.
"""
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    sec, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def segments_to_srt(segments) -> str:
    lines = []
    for i, (start, end, text) in enumerate(segments, start=1):
        lines.append(f"{i}\n{_ts(start)} --> {_ts(end)}\n{text.strip()}\n")
    return "\n".join(lines)


def parse_srt(srt_text: str) -> list[tuple[float, float, str]]:
    """Return [(start_s, end_s, text), ...] from an SRT body."""
    out = []
    for block in srt_text.strip().split("\n\n"):
        lines = block.split("\n")
        if len(lines) < 3:
            continue
        times = lines[1]
        m = re.match(
            r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})",
            times)
        if not m:
            continue
        sh, sm, ss, sms, eh, em, es, ems = map(int, m.groups())
        start = sh * 3600 + sm * 60 + ss + sms / 1000
        end = eh * 3600 + em * 60 + es + ems / 1000
        text = " ".join(lines[2:])
        out.append((start, end, text))
    return out


def transcribe(audio_path: Path, srt_path: Path, *, model_size: str = "base") -> Path:
    from faster_whisper import WhisperModel  # imported lazily; heavy dependency
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(str(audio_path), word_timestamps=False)
    tuples = [(s.start, s.end, s.text) for s in segments]
    srt_path.write_text(segments_to_srt(tuples))
    return srt_path


def burn_captions_into_frames(
    shots_dir: Path,
    srt_path: Path,
    voiceover_duration_s: float,
    fps: int = 25,
    *,
    height_ratio: float = 0.20,
    font_size: int = 56,
    text_color=(255, 255, 255),
    band_color=(0, 0, 0),
    band_alpha: int = 170,
    max_chars_per_line: int = 56,
) -> int:
    """Overlay SRT caption text onto each shot PNG. Mutates files in place.

    Distributes the voiceover duration evenly across shots, then for each
    shot determines which caption intervals fall within its slice and bakes
    the text onto the frame.

    Returns the number of frames modified.
    """
    shots = sorted(shots_dir.glob("[0-9][0-9].png"))
    n = len(shots)
    if n == 0:
        return 0

    if not srt_path.exists():
        return 0

    captions = parse_srt(srt_path.read_text())
    if not captions:
        return 0

    per_shot = voiceover_duration_s / n
    font = _font(font_size)

    frames_modified = 0
    for i, shot_path in enumerate(shots):
        shot_start = i * per_shot
        shot_end = (i + 1) * per_shot

        relevant = []
        for c_start, c_end, c_text in captions:
            if c_end >= shot_start and c_start <= shot_end:
                relevant.append((c_start, c_end, c_text))
        if not relevant:
            continue

        combined = " ".join(t for _, _, t in relevant)
        # Drop leading "Number." type artifacts Whisper sometimes adds
        if combined.lower().startswith("number."):
            combined = combined[7:].lstrip()
        wrapped = _wrap_text(combined, max_chars_per_line)

        img = Image.open(shot_path).convert("RGBA")
        img_w, img_h = img.size
        band_h = int(img_h * height_ratio)

        overlay = Image.new("RGBA", (img_w, band_h), (*band_color, band_alpha))
        band_y = img_h - band_h - int(img_h * 0.04)
        img.alpha_composite(overlay, (0, band_y))

        draw = ImageDraw.Draw(img)
        line_height = font_size + 8
        total_text_h = line_height * len(wrapped)
        start_y = band_y + max(0, (band_h - total_text_h) // 2)
        for li, line in enumerate(wrapped):
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            tx = max(0, (img_w - tw) // 2)
            ty = start_y + li * line_height
            draw.text((tx, ty), line, font=font, fill=text_color)

        img.convert("RGB").save(shot_path)
        frames_modified += 1

    return frames_modified


def _wrap_text(text: str, max_chars: int) -> list[str]:
    """Greedy word-wrap to max_chars per line."""
    words = text.split()
    lines = []
    cur = []
    for w in words:
        if sum(len(x) for x in cur) + len(cur) + len(w) <= max_chars:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines or [""]