import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from studio.config import load_settings
from studio.state import EpisodeState, Stage
from studio import tts, images, music, captions, assemble, thumbnail, upload


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
        prompts = ["a cinematic marble statue, dramatic light, dark background"]
    return " ".join(narration), prompts


def _voiceover_seconds(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _image_files(shots_dir: Path) -> list[Path]:
    return sorted(shots_dir.glob("[0-9][0-9].png"))


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

    mu = music.compose(s, "slow ambient stoic pad, no percussion, contemplative",
                       episode_dir / "music.wav")
    st.record_usage("music", mu.usage)

    captions.transcribe(episode_dir / "voiceover.wav", episode_dir / "captions.srt")

    total = _voiceover_seconds(episode_dir / "voiceover.wav")
    shot_files = _image_files(episode_dir / "shots")
    assemble.render(
        shots=shot_files, voiceover=episode_dir / "voiceover.wav",
        music=episode_dir / "music.wav", captions=episode_dir / "captions.srt",
        out=episode_dir / "video.mp4", total_seconds=total)

    thumbnail.compose(shot_files[0], _title_from(episode_dir),
                      episode_dir / "thumb.png")

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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="studio.pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("render", "publish"):
        p = sub.add_parser(name)
        p.add_argument("episode_dir")
    args = parser.parse_args(argv)
    if args.cmd == "render":
        render_episode(Path(args.episode_dir))
    else:
        print(publish_episode(Path(args.episode_dir)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
