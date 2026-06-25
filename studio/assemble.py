"""Video assembly — combines shots, voiceover, music, sound fx, and (optionally)
burned-in captions into the final mp4.

Filter graph layout (with N shots, V audio inputs):

    [shot_0 ... shot_N-1]  -- each gets zoompan + scale --> [v0 ... vN-1]
        --> concat --> [vout]                              (video chain)

    [voiceover] --> [vfull]
    [music]      --> volume=0.18 --> [mlow]
    [vfull][mlow]--> amix=inputs=2 --> [music_mix]
    [sfx_0 ... sfx_K-1] --> atrim + adelay --> [sfx_chain]
    [music_mix][sfx_chain] --> amix=inputs=1+K --> [aout]   (audio chain)

    [vout][aout] --> final mp4

Optional: --captions path/to.srt adds the subtitles filter before [vout] to
burn captions into the video (requires libass in the ffmpeg build).
Optional: --intro path/to.png + --outro path/to.png prepend/append title cards.

The assembly writes the actual ffmpeg args to a debug file next to the output
for easy inspection: out.ffmpeg.log
"""
import json
import shlex
import subprocess
from pathlib import Path

FPS = 25
W, H = 1920, 1080


def _pad_to_frames(n: int, total: int) -> int:
    """Pad n up to total if it's a little short (cumulative drift tolerance)."""
    return max(n, total)


def build_ffmpeg_args(*, shots: list[Path], voiceover: Path, music: Path,
                      out: Path, total_seconds: float,
                      sfx_events: list[dict] | None = None,
                      sfx_resolver=None,
                      captions_srt: Path | None = None,
                      intro_card: Path | None = None,
                      outro_card: Path | None = None,
                      color_grade: bool = False) -> list[str]:
    """Return the ffmpeg command line for the full assembly.

    sfx_events: list of {name, offset_s} dicts (output of sound_fx.parse_script).
    sfx_resolver: callable taking an event dict and returning the wav path or None.
    captions_srt: optional SRT path to burn into the video.
    intro_card/outro_card: optional PNG paths prepended/appended as stills.
    """
    n = len(shots)
    if n == 0:
        raise ValueError("at least one shot is required")

    # Compute exact per-shot duration. Round to nearest frame to avoid drift.
    total_frames = int(round(total_seconds * FPS))
    per_shot_frames = total_frames // n
    # Distribute leftover frames across the first few shots (1 each)
    leftover = total_frames - (per_shot_frames * n)

    args: list[str] = ["ffmpeg", "-y"]
    filter_parts: list[str] = []

    # Optional intro card (treated as shot -1)
    intro_frames = int(round(FPS * 3))  # 3 seconds
    if intro_card:
        args += ["-loop", "1", "-t", f"{intro_frames / FPS:.3f}", "-i", str(intro_card)]

    # Per-image inputs: ONE still each (no -loop/-t). zoompan's d= (in the video
    # chain below) expands each still into its shot-length run of frames.
    # NB: looping the input here is the classic zoompan trap — zoompan emits d
    # frames *per input frame*, so a looped shot 0 (≈1000 frames) would alone
    # fill the whole video and shots 1..N would never render.
    for i, sh in enumerate(shots):
        args += ["-i", str(sh)]

    # Outro card
    outro_frames = int(round(FPS * 6))  # 6 seconds
    if outro_card:
        args += ["-loop", "1", "-t", f"{outro_frames / FPS:.3f}", "-i", str(outro_card)]

    # Audio inputs (voiceover + music + optional sfx)
    args += ["-i", str(voiceover), "-i", str(music)]

    sfx_paths: list[Path] = []
    sfx_offsets: list[float] = []
    if sfx_events and sfx_resolver:
        for ev in sfx_events:
            p = sfx_resolver(ev)
            if p is None:
                continue
            sfx_paths.append(p)
            sfx_offsets.append(ev.get("offset_s", 0.0))
            args += ["-i", str(p)]

    # === VIDEO CHAIN ===
    # Index of the first image input (accounting for optional intro card)
    img_offset = 1 if intro_card else 0
    for i in range(n):
        this_frames = per_shot_frames + (1 if i < leftover else 0)
        # Use force_original_aspect_ratio + scale to ensure consistent sizing;
        # zoompan with explicit d= produces exactly this_frames output frames.
        filter_parts.append(
            f"[{i + img_offset}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"zoompan=z='min(zoom+0.0005,1.15)':d={this_frames}:"
            f"s={W}x{H}:fps={FPS}[v{i}]"
        )

    # Concat video inputs (intro + shots + outro if present)
    concat_inputs = []
    if intro_card:
        # Need to pad intro into a labeled video too
        filter_parts.append(
            f"[{img_offset - 1}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"trim=duration={intro_frames / FPS},setpts=PTS-STARTPTS[vintro]"
        )
        concat_inputs.append("[vintro]")
    for i in range(n):
        concat_inputs.append(f"[v{i}]")
    if outro_card:
        outro_idx = n + img_offset
        filter_parts.append(
            f"[{outro_idx}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"trim=duration={outro_frames / FPS},setpts=PTS-STARTPTS[voutro]"
        )
        concat_inputs.append("[voutro]")

    concat_label = "vconcat"
    filter_parts.append(
        f"{''.join(concat_inputs)}concat=n={len(concat_inputs)}:v=1:a=0[{concat_label}]"
    )

    # Optional captions burn-in
    vout_label = concat_label
    if captions_srt:
        # subtitles filter requires libass
        filter_parts.append(
            f"[{concat_label}]subtitles={shlex.quote(str(captions_srt))}:"
            f"force_style='FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,"
            f"OutlineColour=&H80000000,BackColour=&H80000000,BorderStyle=4,"
            f"Outline=0,Shadow=0,MarginV=60,Alignment=2'[vsubbed]"
        )
        vout_label = "vsubbed"

    # Optional uniform color grade — a subtle warm push toward the brand palette
    # (warm shadows/mids, cooled highlights, slightly lifted contrast, gently
    # desaturated) so every episode shares one tone regardless of generation drift.
    if color_grade:
        filter_parts.append(
            f"[{vout_label}]eq=contrast=1.06:saturation=0.96,"
            f"colorbalance=rs=0.02:bs=-0.03:rm=0.03:bm=-0.03:rh=0.02:bh=-0.02[vgraded]"
        )
        vout_label = "vgraded"

    # === AUDIO CHAIN ===
    # voiceover is at index (n + img_offset + (1 if outro else 0))
    vo_idx = n + img_offset + (1 if outro_card else 0)
    music_idx = vo_idx + 1

    # Voice: when an intro card precedes the shots, delay the narration so it
    # starts when the first shot starts (not talking over the intro card).
    intro_seconds = (intro_frames / FPS) if intro_card else 0.0
    if intro_seconds:
        intro_ms = int(round(intro_seconds * 1000))
        filter_parts.append(f"[{vo_idx}:a]adelay={intro_ms}|{intro_ms}[vo]")
        voice_label = "vo"
    else:
        voice_label = f"{vo_idx}:a"

    # Music ducked under the voice. With cards the video runs longer than the
    # narration (intro + shots + outro), so the mix must span the longest input
    # (the music, which the pipeline loops to the full video length) and the
    # music fades out under the outro. Without cards, the narration drives length.
    has_cards = bool(intro_card or outro_card)
    if has_cards:
        total_video = (intro_seconds + total_seconds
                       + (outro_frames / FPS if outro_card else 0.0))
        fade_start = max(0.0, total_video - 2.0)
        filter_parts.append(
            f"[{music_idx}:a]volume=0.18,afade=t=out:st={fade_start:.3f}:d=2[mlow]")
        mix_dur = "longest"
    else:
        filter_parts.append(f"[{music_idx}:a]volume=0.18[mlow]")
        mix_dur = "first"
    filter_parts.append(
        f"[{voice_label}][mlow]amix=inputs=2:duration={mix_dur}:dropout_transition=0[vmix]")

    # Add SFX: each gets adelay + atrim to its duration, then mixed in
    aout_label = "vmix"
    if sfx_paths:
        sfx_filters = []
        for j, (path, off) in enumerate(zip(sfx_paths, sfx_offsets)):
            # Shift SFX by the intro duration so a beat-aligned cue (e.g. the
            # phone-ring on shot 0) lands on its shot, not during the intro card.
            ms = int(round((off + intro_seconds) * 1000))
            sfx_filters.append(
                f"[{vo_idx + 2 + j}:a]adelay={ms}|{ms},apad[sfx{j}]"
            )
        # Mix all sfx together, then mix with voiceover+music
        if len(sfx_paths) == 1:
            filter_parts.append(sfx_filters[0])
            filter_parts.append(
                f"[vmix][sfx0]amix=inputs=2:duration=first:dropout_transition=0[aout]"
            )
        else:
            for sf in sfx_filters:
                filter_parts.append(sf)
            sfx_inputs = "".join(f"[sfx{j}]" for j in range(len(sfx_paths)))
            filter_parts.append(
                f"{sfx_inputs}amix=inputs={len(sfx_paths)}:duration=longest:dropout_transition=0[sfxall]"
            )
            filter_parts.append(
                f"[vmix][sfxall]amix=inputs=2:duration=first:dropout_transition=0[aout]"
            )
        aout_label = "aout"

    # Combine filter parts
    args += ["-filter_complex", ";\n".join(filter_parts)]
    args += ["-map", f"[{vout_label}]", "-map", f"[{aout_label}]"]
    args += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)]

    return args


def render(*, shots: list[Path], voiceover: Path, music: Path, out: Path,
           total_seconds: float, **kwargs) -> Path:
    """Run the assembly. Returns out path. Writes a debug .ffmpeg.log alongside.

    Extra kwargs forwarded to build_ffmpeg_args: sfx_events, sfx_resolver,
    captions_srt, intro_card, outro_card.
    """
    args = build_ffmpeg_args(
        shots=shots, voiceover=voiceover, music=music, out=out,
        total_seconds=total_seconds, **kwargs)
    # Write debug log
    log_path = out.with_suffix(".ffmpeg.log")
    log_path.write_text(" ".join(shlex.quote(a) if " " in a or ";" in a or "|" in a else a
                                for a in args))
    subprocess.run(args, check=True)
    return out