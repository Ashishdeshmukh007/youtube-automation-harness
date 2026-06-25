import subprocess
from pathlib import Path

FPS = 25
W, H = 1920, 1080


def build_ffmpeg_args(*, shots: list[Path], voiceover: Path, music: Path,
                      captions: Path, out: Path, total_seconds: float) -> list[str]:
    n = len(shots)
    per_shot = total_seconds / n
    frames = int(round(per_shot * FPS))

    args: list[str] = ["ffmpeg", "-y"]
    # image inputs (looped to the per-shot duration)
    for sh in shots:
        args += ["-loop", "1", "-t", f"{per_shot:.3f}", "-i", str(sh)]
    # audio inputs
    args += ["-i", str(voiceover), "-i", str(music)]

    # per-image Ken Burns zoom, then concat
    filters = []
    for i in range(n):
        filters.append(
            f"[{i}:v]scale={W}:-2,zoompan=z='min(zoom+0.0005,1.15)':"
            f"d={frames}:s={W}x{H}:fps={FPS}[v{i}]"
        )
    concat_inputs = "".join(f"[v{i}]" for i in range(n))
    filters.append(f"{concat_inputs}concat=n={n}:v=1:a=0[vcat]")
    # burn captions
    filters.append(f"[vcat]subtitles={captions}[vout]")
    # mix: voiceover full, music ducked to 0.18
    va, ma = n, n + 1  # audio input indices
    filters.append(
        f"[{ma}:a]volume=0.18[mlow];"
        f"[{va}:a][mlow]amix=inputs=2:duration=first:dropout_transition=0[aout]"
    )

    args += ["-filter_complex", ";".join(filters)]
    args += ["-map", "[vout]", "-map", "[aout]"]
    args += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)]
    return args


def render(*, shots: list[Path], voiceover: Path, music: Path, captions: Path,
           out: Path, total_seconds: float) -> Path:
    args = build_ffmpeg_args(shots=shots, voiceover=voiceover, music=music,
                             captions=captions, out=out, total_seconds=total_seconds)
    subprocess.run(args, check=True)
    return out
