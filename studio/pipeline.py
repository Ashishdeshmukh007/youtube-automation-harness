import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from studio.config import load_settings
from studio.state import EpisodeState, Stage
from studio import (tts, images, music, captions, assemble, thumbnail, upload,
                    cards, sound_fx)

# Design-language constants: standard card durations and the brand caption look.
INTRO_SECONDS = 3.0
OUTRO_SECONDS = 6.0
_CAPTION_TEXT = (224, 200, 160)   # off-white #E0C8A0
_CAPTION_BAND = (58, 38, 32)      # warm shadow #3A2620
_CAPTION_BAND_ALPHA = 180


def _script_shots(script_path: Path) -> tuple[str, list[str]]:
    """Return (narration_text, image_prompts). Lines starting 'Shot:' are visual
    prompts; everything else is narration."""
    narration, prompts = [], []
    for line in script_path.read_text().splitlines():
        if line.strip().lower().startswith("shot:"):
            prompts.append(line.split(":", 1)[1].strip())
        elif line.strip():
            narration.append(line.strip())
    if not prompts:
        prompts = ["a cinematic still of ancient India at dawn, Himalayan foothills, "
                   "soft contemplative light, a weathered palm-leaf manuscript, "
                   "no text, no people, muted earthy tones"]
    return " ".join(narration), prompts


def _voiceover_seconds(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _image_files(shots_dir: Path) -> list[Path]:
    return sorted(shots_dir.glob("[0-9][0-9].png"))


def _loop_audio(src: Path, dst: Path, seconds: float) -> Path:
    """Loop a (short) audio file to cover `seconds`, with a 2s fade-out tail.
    MiniMax music caps at ~70s, so a full episode needs the bed looped."""
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-stream_loop", "-1", "-i", str(src), "-t", f"{seconds:.3f}",
         "-af", f"afade=t=out:st={max(0.0, seconds - 2):.3f}:d=2", str(dst)],
        check=True)
    return dst


def _burned_shots_dir(episode_dir: Path, total_seconds: float) -> Path:
    """Copy the shots and burn the captions onto the copies (brand palette),
    leaving the originals clean (e.g. for the thumbnail). Returns the copy dir."""
    src = episode_dir / "shots"
    dst = episode_dir / "shots_burned"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for p in _image_files(src):
        shutil.copy(p, dst / p.name)
    captions.burn_captions_into_frames(
        dst, episode_dir / "captions.srt", total_seconds, fps=assemble.FPS,
        text_color=_CAPTION_TEXT, band_color=_CAPTION_BAND,
        band_alpha=_CAPTION_BAND_ALPHA)
    return dst


def render_episode(episode_dir: Path, settings=None) -> None:
    episode_dir = Path(episode_dir)
    st = EpisodeState.load(episode_dir)
    st.require("script")
    st.set_stage(Stage.RENDERING)
    s = settings or load_settings()

    narration, prompts = _script_shots(episode_dir / "script.md")

    vo = tts.synthesize(s, narration, episode_dir / "voiceover.wav")
    st.record_usage("tts", vo.usage)

    im = images.generate(s, prompts, episode_dir / "shots")
    st.record_usage("images", im.usage)

    mu = music.compose(s, "slow cinematic ambient drone, contemplative and calm, "
                       "subtle bansuri flute and tanpura, no percussion, meditative, "
                       "modern and understated (not devotional)",
                       episode_dir / "music.wav")
    st.record_usage("music", mu.usage)

    # Captions: an .srt sidecar (uploaded as a YouTube subtitle track) AND burned
    # onto the frames for on-screen legibility (silent autoplay / mobile).
    captions.transcribe(episode_dir / "voiceover.wav", episode_dir / "captions.srt")

    total = _voiceover_seconds(episode_dir / "voiceover.wav")

    # Standard design-language bookends + looped bed covering the full runtime.
    cards.render_intro(episode_dir / "intro.png")
    cards.render_outro(episode_dir / "outro.png")
    total_video = INTRO_SECONDS + total + OUTRO_SECONDS
    music_full = _loop_audio(episode_dir / "music.wav",
                             episode_dir / "music_full.wav", total_video)

    shot_files = _image_files(_burned_shots_dir(episode_dir, total))
    sfx_events = sound_fx.parse_script((episode_dir / "script.md").read_text())
    assemble.render(
        shots=shot_files, voiceover=episode_dir / "voiceover.wav",
        music=music_full, out=episode_dir / "video.mp4", total_seconds=total,
        sfx_events=sfx_events, sfx_resolver=sound_fx.resolve_event,
        intro_card=episode_dir / "intro.png", outro_card=episode_dir / "outro.png",
        color_grade=True)

    # Thumbnail from the clean (un-captioned) first shot.
    thumbnail.compose(_image_files(episode_dir / "shots")[0],
                      _title_from(episode_dir), episode_dir / "thumb.png")

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
