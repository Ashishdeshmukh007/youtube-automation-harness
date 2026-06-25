from pathlib import Path


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


def transcribe(audio_path: Path, srt_path: Path, *, model_size: str = "base") -> Path:
    from faster_whisper import WhisperModel  # imported lazily; heavy dependency
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(str(audio_path), word_timestamps=False)
    tuples = [(s.start, s.end, s.text) for s in segments]
    srt_path.write_text(segments_to_srt(tuples))
    return srt_path
