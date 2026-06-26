from pathlib import Path
from studio.assemble import build_ffmpeg_args


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
    # video + audio outputs mapped, music ducked under voiceover
    joined = " ".join(args)
    assert "concat=n=2" in joined
    assert "amix=inputs=2" in joined
    # music bed sits very low under the narration
    assert "volume=0.05" in joined
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
    """When intro/outro cards are provided, concat should include them."""
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
    # intro (3s) + 2 shots + outro (6s) = 4 video inputs to concat
    assert "concat=n=4" in joined
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
