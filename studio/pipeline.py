import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from studio.config import load_settings
from studio.state import EpisodeState, Stage
from studio import (tts, images, music, captions, assemble, thumbnail, upload,
                    sound_fx, video_clips)

# Reusable animated brand bookends (generated once, used by every episode).
_BRAND = Path(__file__).resolve().parents[1] / "brand"
BOOKEND_INTRO = _BRAND / "intro.mp4"
BOOKEND_OUTRO = _BRAND / "outro.mp4"

# Generic motion prompt for animating a HERO ('Clip:') still into a clip.
_CLIP_MOTION = ("Gentle cinematic motion: a slow, subtle push-in; dust, light, hair "
                "and cloth drift softly; the subjects hold their poses. Reverent, "
                "filmic, no distortion.")


def _script_shots(script_path: Path) -> tuple[str, list[str]]:
    """Return (narration_text, image_prompts).

    Lines starting 'Shot:' are visual prompts. Narration is the spoken text only —
    NOT the production markers, which must never reach the TTS:
      - 'Sfx:' sound cues
      - bracketed stage directions ('[beat]', '[end]')
      - markdown headers ('# Title')
    """
    narration, prompts = [], []
    for line in script_path.read_text().splitlines():
        s = line.strip()
        if not s:
            continue
        low = s.lower()
        if low.startswith("shot:"):
            prompts.append(s.split(":", 1)[1].strip())
        elif low.startswith("sfx:"):
            continue  # sound cue, not spoken
        elif s.startswith("[") and s.endswith("]"):
            continue  # stage direction, not spoken
        elif s.startswith("#"):
            continue  # markdown header, not spoken
        else:
            narration.append(s)
    if not prompts:
        prompts = ["a cinematic still of ancient India at dawn, Himalayan foothills, "
                   "soft contemplative light, a weathered palm-leaf manuscript, "
                   "no text, no people, muted earthy tones"]
    return " ".join(narration), prompts


def _script_beats(script_path: Path) -> tuple[str, list[dict]]:
    """Parse the script into ordered visual beats, each tied to the narration it
    covers — so every image reflects exactly what is being said while it's on screen.

      Shot: <prompt>   -> a still beat (Ken Burns)
      Clip: <prompt>   -> an animated HERO beat (motion only where it has impact)

    Each beat accumulates the narration lines that follow it (until the next beat);
    `words` is used to size the beat's on-screen duration proportional to its
    narration. Returns (full_narration, beats[{kind, prompt, words}]).
    """
    beats: list[dict] = []
    narration: list[str] = []
    for line in script_path.read_text().splitlines():
        s = line.strip()
        if not s:
            continue
        low = s.lower()
        if low.startswith("shot:") or low.startswith("clip:"):
            kind = "clip" if low.startswith("clip:") else "still"
            beats.append({"kind": kind, "prompt": s.split(":", 1)[1].strip(), "words": 0})
        elif low.startswith("sfx:") or s.startswith("#") or (s.startswith("[") and s.endswith("]")):
            continue
        else:
            narration.append(s)
            if beats:
                beats[-1]["words"] += len(s.split())
    return " ".join(narration), beats


def _voiceover_seconds(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _image_files(shots_dir: Path) -> list[Path]:
    return sorted(shots_dir.glob("[0-9][0-9].png"))


def _normalize_audio(src: Path, dst: Path) -> Path:
    """Loudness-normalize the voice to an even level (the TTS drifts in volume over
    long narration) as a clean 44.1k mono wav. Done as a SEPARATE pre-pass —
    loudnorm inside the assembly filtergraph corrupts the mux (non-monotonic DTS)."""
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", "-ac", "1", str(dst)],
        check=True)
    return dst


def _loop_audio(src: Path, dst: Path, seconds: float) -> Path:
    """Loop a (short) audio file to cover `seconds`, with a 2s fade-out tail.
    MiniMax music caps at ~70s, so a full episode needs the bed looped."""
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-stream_loop", "-1", "-i", str(src), "-t", f"{seconds:.3f}",
         "-af", f"afade=t=out:st={max(0.0, seconds - 2):.3f}:d=2", str(dst)],
        check=True)
    return dst


def _concat_bookends(intro: Path, body: Path, outro: Path, out: Path) -> Path:
    """Bracket the episode body with the reusable animated bookends. Each input is
    normalized (1080p / 25fps / 44.1k stereo) and concatenated (re-encoded)."""
    norm = "scale=1920:1080,fps=25,setsar=1"
    af = "aformat=sample_rates=44100:channel_layouts=stereo"
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(intro), "-i", str(body), "-i", str(outro), "-filter_complex",
        f"[0:v]{norm}[v0];[0:a]{af}[a0];[1:v]{norm}[v1];[1:a]{af}[a1];"
        f"[2:v]{norm}[v2];[2:a]{af}[a2];[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-movflags", "+faststart", str(out)], check=True)
    return out


def render_episode(episode_dir: Path, settings=None) -> None:
    episode_dir = Path(episode_dir)
    st = EpisodeState.load(episode_dir)
    st.require("script")
    st.set_stage(Stage.RENDERING)
    s = settings or load_settings()

    narration, beats = _script_beats(episode_dir / "script.md")

    vo = tts.synthesize(s, narration, episode_dir / "voiceover.wav")
    st.record_usage("tts", vo.usage)

    # One still per beat, in narration order (so each image matches its voiceover).
    im = images.generate(s, [b["prompt"] for b in beats], episode_dir / "shots")
    st.record_usage("images", im.usage)

    mu = music.compose(s, "slow cinematic ambient drone, contemplative and calm, "
                       "subtle bansuri flute and tanpura, no percussion, meditative, "
                       "modern and understated (not devotional)",
                       episode_dir / "music.wav")
    st.record_usage("music", mu.usage)

    # Captions: an .srt sidecar only (optional YouTube subtitle track). Not burned
    # into the frames — we rely on YouTube's captions and keep the visuals clean.
    captions.transcribe(episode_dir / "voiceover.wav", episode_dir / "captions.srt")

    total = _voiceover_seconds(episode_dir / "voiceover.wav")

    # Looped music bed (body length) + loudness-normalized voice.
    music_full = _loop_audio(episode_dir / "music.wav",
                             episode_dir / "music_full.wav", total)
    voice_norm = _normalize_audio(episode_dir / "voiceover.wav",
                                  episode_dir / "voiceover_norm.wav")

    # Hybrid timeline: each beat is on screen for its share of the narration (so
    # visuals track the voiceover); HERO 'Clip:' beats are animated, the rest are
    # Ken-Burns stills. We animate only where motion has real impact.
    stills = _image_files(episode_dir / "shots")
    clips_dir = episode_dir / "clips"; clips_dir.mkdir(exist_ok=True)
    total_words = sum(b["words"] for b in beats) or 1
    segments = []
    for i, b in enumerate(beats):
        secs = max(2.0, b["words"] / total_words * total)
        if b["kind"] == "clip" and s.fal_key:
            clip = video_clips.animate(s.fal_key, stills[i], _CLIP_MOTION,
                                       clips_dir / f"{i:02d}.mp4")
            segments.append({"kind": "clip", "path": clip, "seconds": secs})
        else:
            segments.append({"kind": "still", "path": stills[i], "seconds": secs})

    # Body (graded; captions NOT burned — YouTube auto-captions), then bookends.
    sfx_events = sound_fx.parse_script((episode_dir / "script.md").read_text())
    body = episode_dir / "body.mp4"
    assemble.render_hybrid(
        segments=segments, voiceover=voice_norm, music=music_full, out=body,
        total_seconds=total, sfx_events=sfx_events,
        sfx_resolver=sound_fx.resolve_event, color_grade=True)
    _concat_bookends(BOOKEND_INTRO, body, BOOKEND_OUTRO, episode_dir / "video.mp4")

    thumbnail.compose(stills[0], _title_from(episode_dir), episode_dir / "thumb.png")

    st.set_stage(Stage.RENDER_REVIEW)


def _title_from(episode_dir: Path) -> str:
    topic = episode_dir / "topic.md"
    if topic.exists():
        first = topic.read_text().strip().splitlines()[0]
        return re.sub(r"^#+\s*", "", first)[:60] or episode_dir.name
    return episode_dir.name


def publish_episode(episode_dir: Path, settings=None) -> str:
    episode_dir = Path(episode_dir)
    st = EpisodeState.load(episode_dir)
    st.require("video")
    st.set_stage(Stage.PUBLISHING)
    s = settings or load_settings()
    meta = json.loads((episode_dir / "metadata.json").read_text())
    video_id = upload.upload(
        episode_dir / "video.mp4", episode_dir / "thumb.png", meta,
        client_secret=s.youtube_client_secret, token=s.youtube_token)
    st.data["youtube_video_id"] = video_id
    st.set_stage(Stage.PUBLISHED)
    return video_id


# Gate name -> stage the episode advances to once that gate is approved.
_GATE_STAGE = {"script": Stage.SCRIPT_APPROVED, "video": Stage.APPROVED}


def approve_episode(episode_dir: Path, gate: str) -> None:
    """Record a human gate approval and advance the episode's stage."""
    if gate not in _GATE_STAGE:
        raise ValueError(f"unknown gate: {gate!r} (expected one of {list(_GATE_STAGE)})")
    st = EpisodeState.load(Path(episode_dir))
    st.approve(gate)
    st.set_stage(_GATE_STAGE[gate])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="studio.pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("render", "publish"):
        p = sub.add_parser(name)
        p.add_argument("episode_dir")
    ap = sub.add_parser("approve")
    ap.add_argument("episode_dir")
    ap.add_argument("--gate", required=True, choices=list(_GATE_STAGE))
    args = parser.parse_args(argv)
    if args.cmd == "render":
        render_episode(Path(args.episode_dir))
    elif args.cmd == "approve":
        approve_episode(Path(args.episode_dir), args.gate)
    else:
        print(publish_episode(Path(args.episode_dir)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
