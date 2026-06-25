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
    assert "volume=0.18" in joined
    assert args[-1] == str(tmp_path / "video.mp4")


def test_per_shot_duration_is_total_over_count(tmp_path):
    shots = [tmp_path / "00.png", tmp_path / "01.png"]
    for sh in shots:
        sh.write_bytes(b"x")
    args = build_ffmpeg_args(
        shots=shots, voiceover=tmp_path / "v.wav", music=tmp_path / "m.wav",
        out=tmp_path / "o.mp4", total_seconds=20.0,
    )
    joined = " ".join(args)
    assert "d=250" in joined  # 10s per shot * 25 fps = 250 frames
