from pathlib import Path
from studio.assemble import build_ffmpeg_args, build_hybrid_args


def test_hybrid_mixes_stills_and_clips(tmp_path):
    """A hybrid body: stills get Ken-Burns zoompan, clips play as video, timed.
    Adjacent segments cross-dissolve via xfade (cinematic, contemplative)."""
    still = tmp_path / "00.png"; still.write_bytes(b"x")
    clip = tmp_path / "01.mp4"; clip.write_bytes(b"x")
    segments = [
        {"kind": "still", "path": still, "seconds": 6.0},
        {"kind": "clip", "path": clip, "seconds": 5.0},
    ]
    args = build_hybrid_args(
        segments=segments, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=11.0)
    joined = " ".join(args)
    assert str(still) in args and str(clip) in args
    assert "zoompan" in joined                 # still -> Ken Burns
    # Clip is the LAST segment so it absorbs the (n-1)*xfade overlap to keep
    # the body duration equal to the voiceover: 5.0 + 0.5 = 5.5s.
    assert "trim=duration=5.500" in joined
    assert "xfade=transition=fade" in joined    # cross-dissolve chain
    assert "concat=n=2" not in joined           # body no longer hard-cut concat'd
    assert "volume=0.03" in joined              # ducked music bed


def test_build_args_includes_inputs_and_outputs(tmp_path):
    shots = [tmp_path / "00.png", tmp_path / "01.png"]
    for sh in shots:
        sh.write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=shots,
        voiceover=tmp_path / "voiceover.wav",
        music=tmp_path / "music.wav",
        out=tmp_path / "video.mp4",
        total_seconds=20.0,
    )
    assert args[0] == "ffmpeg"
    assert "-y" in args
    # both stills are inputs
    assert str(shots[0]) in args and str(shots[1]) in args
    # voiceover and music inputs present
    assert str(tmp_path / "voiceover.wav") in args
    assert str(tmp_path / "music.wav") in args
    # Body shots cross-dissolve (no concat for the body when no cards).
    # Audio chain and output mapping unchanged.
    joined = " ".join(args)
    assert "xfade=transition=fade" in joined
    assert "amix=inputs=2" in joined
    # music bed sits very low under the narration
    assert "volume=0.03" in joined
    assert args[-1] == str(tmp_path / "video.mp4")


def test_output_is_full_hd_not_downscaled(tmp_path):
    """Shots must render at 1920x1080; guard against the hd480 downscale regression."""
    shots = [tmp_path / "00.png"]
    shots[0].write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=shots, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=10.0,
    )
    joined = " ".join(args)
    assert "s=1920x1080" in joined
    assert "hd480" not in joined


def test_shots_are_single_stills_not_looped(tmp_path):
    """Shots must be fed as single frames; looping them makes zoompan emit
    d frames per looped input frame, so shot 0 alone fills the whole video."""
    shots = [tmp_path / "00.png", tmp_path / "01.png"]
    for sh in shots:
        sh.write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=shots, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=20.0,
    )
    # No intro/outro here, so nothing should be looped.
    assert "-loop" not in args
    # Each shot still appears exactly once as an input.
    assert args.count(str(shots[0])) == 1
    assert args.count(str(shots[1])) == 1


def test_per_shot_duration_is_total_over_count(tmp_path):
    shots = [tmp_path / "00.png", tmp_path / "01.png"]
    for sh in shots:
        sh.write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=shots, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=20.0,
    )
    joined = " ".join(args)
    # 10s per shot * 25 fps = 250 frames per zoompan
    assert "d=250" in joined


def test_intro_outro_appended(tmp_path):
    """When intro/outro cards are provided, cards concat against the body — but
    the body itself cross-dissolves (cards stay hard-cut to preserve title
    boundaries)."""
    shots = [tmp_path / "00.png", tmp_path / "01.png"]
    for sh in shots:
        sh.write_bytes(b"x")
    intro = tmp_path / "intro.png"
    intro.write_bytes(b"x")
    outro = tmp_path / "outro.png"
    outro.write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=shots, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=20.0,
        intro_card=intro, outro_card=outro,
    )
    joined = " ".join(args)
    # intro (3s) + body (xfade chain) + outro (6s) = 3 hard-cut concat inputs
    assert "concat=n=3" in joined
    assert "xfade=transition=fade" in joined
    assert str(intro) in joined
    assert str(outro) in joined


def test_color_grade_applied_when_requested(tmp_path):
    """A uniform grade ties every episode to one look."""
    shots = [tmp_path / "00.png"]
    shots[0].write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=shots, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=10.0, color_grade=True)
    assert "colorbalance" in " ".join(args)


def test_no_color_grade_by_default(tmp_path):
    shots = [tmp_path / "00.png"]
    shots[0].write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=shots, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=10.0)
    assert "colorbalance" not in " ".join(args)


def test_intro_delays_voiceover_and_shifts_sfx(tmp_path):
    """With a 3s intro card, the voiceover must start when the shots start (not
    over the intro), and SFX offsets must shift by the intro duration too."""
    shots = [tmp_path / "00.png", tmp_path / "01.png"]
    for sh in shots:
        sh.write_bytes(b"x")
    intro = tmp_path / "intro.png"; intro.write_bytes(b"x")
    outro = tmp_path / "outro.png"; outro.write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=shots, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=20.0,
        intro_card=intro, outro_card=outro,
        sfx_events=[{"name": "bell", "offset_s": 2.0}],
        sfx_resolver=lambda e: tmp_path / f"{e['name']}.wav",
    )
    joined = " ".join(args)
    # voiceover delayed by the 3s intro
    assert "adelay=3000|3000" in joined
    # bell at 2.0s + 3s intro = 5.0s
    assert "adelay=5000|5000" in joined


def test_no_intro_means_no_voiceover_delay(tmp_path):
    """Without an intro card, the voiceover is not delayed (no spurious adelay)."""
    shots = [tmp_path / "00.png"]
    shots[0].write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=shots, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=10.0,
    )
    assert "adelay" not in " ".join(args)


def test_sfx_added_as_inputs(tmp_path):
    """SFX events should become audio inputs in the filter graph."""
    shots = [tmp_path / "00.png"]
    shots[0].write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=shots, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=10.0,
        sfx_events=[{"name": "phone-ring", "offset_s": 2.5}],
        sfx_resolver=lambda e: tmp_path / f"{e['name']}.wav",
    )
    # SFX file path should appear in args
    assert "phone-ring.wav" in " ".join(args)
    # adelay filter should be present for offset
    joined = " ".join(args)
    assert "adelay=2500" in joined
    # cue is boosted and mixed without normalization so it's audible
    assert "volume=3.0" in joined
    assert "normalize=0" in joined


def test_sfx_skipped_when_resolver_returns_none(tmp_path):
    """Unknown sfx names should be silently skipped, not crash."""
    shots = [tmp_path / "00.png"]
    shots[0].write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=shots, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=10.0,
        sfx_events=[{"name": "no-such-sound", "offset_s": 0.0}],
        sfx_resolver=lambda e: None,
    )
    # Should not contain any unknown sfx reference
    joined = " ".join(args)
    assert "no-such-sound" not in joined


def test_xfade_chain_count_matches_segments(tmp_path):
    """N segments get N-1 xfade transitions (no fade needed after the last clip)."""
    stills = [tmp_path / f"{i:02d}.png" for i in range(4)]
    for s in stills:
        s.write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=stills, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=20.0)
    joined = " ".join(args)
    assert joined.count("xfade=transition=fade") == 3


def test_xfade_extends_last_shot_to_preserve_total_duration(tmp_path):
    """Each xfade trims ~0.5s of overlap between two adjacent clips. To keep the
    total body duration equal to the voiceover, the LAST shot absorbs the
    cumulative overlap — so the final zoompan has more frames than the others."""
    shots = [tmp_path / f"{i:02d}.png" for i in range(3)]
    for s in shots:
        s.write_bytes(b"x")
    # 30s total at 25fps = 750 frames. 3 shots = 250 each. With 2 xfades
    # (0.5s * 2 = 1.0s = 25 frames), the last shot gets +25 frames.
    args = build_ffmpeg_args(
        shots=shots, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=30.0)
    joined = " ".join(args)
    # First two shots keep their 250-frame zoompan; the last absorbs +25.
    assert "d=250" in joined
    assert "d=275" in joined


def test_xfade_seconds_zero_opts_out_to_hard_cuts(tmp_path):
    """Set xfade_seconds=0 to keep the old hard-cut behavior — useful for A/B
    testing or when a contemplative cold-cut feel is wanted."""
    shots = [tmp_path / "00.png", tmp_path / "01.png"]
    for s in shots:
        s.write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=shots, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=20.0, xfade_seconds=0.0)
    # No xfade filters — we use a single-shot body (no concat since no cards).
    assert "xfade=" not in " ".join(args)


def test_xfade_hybrid_chain_count_matches_segments(tmp_path):
    """Same chain rule for the hybrid path: N segments → N-1 xfade transitions."""
    stills = [tmp_path / f"{i:02d}.png" for i in range(3)]
    for s in stills:
        s.write_bytes(b"x")
    segments = [{"kind": "still", "path": s, "seconds": 5.0} for s in stills]
    args = build_hybrid_args(
        segments=segments, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=15.0)
    joined = " ".join(args)
    assert joined.count("xfade=transition=fade") == 2
