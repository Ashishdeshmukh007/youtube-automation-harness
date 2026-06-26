import json
from pathlib import Path
import pytest
from studio.state import EpisodeState, Stage, GateError
from studio import pipeline


def _seed(dir: Path, stage: str, approvals: dict):
    (dir / "shots").mkdir(parents=True, exist_ok=True)
    (dir / "state.json").write_text(json.dumps({
        "slug": "ep", "stage": stage, "approvals": approvals,
        "usage": [], "created_at": "2026-06-25T09:00:00"}))
    (dir / "script.md").write_text("Shot: a statue.\nShot: a mountain.")


def test_script_shots_excludes_non_narration_lines(tmp_path):
    script = tmp_path / "script.md"
    script.write_text(
        "# The dharma you're skipping\n\n"
        "Shot: a phone screen in the dark\n"
        "Sfx: phone-ring\n\n"
        "It's late at night.\n"
        "[beat]\n"
        "You are on your road.\n"
        "[end]\n")
    narration, prompts = pipeline._script_shots(script)
    assert prompts == ["a phone screen in the dark"]
    # narration must be ONLY the spoken lines
    assert narration == "It's late at night. You are on your road."
    for leak in ("phone-ring", "Sfx", "beat", "end", "dharma you're skipping", "#"):
        assert leak not in narration, f"non-narration leaked into TTS text: {leak!r}"


def test_script_beats_maps_narration_and_marks_hero_clips(tmp_path):
    script = tmp_path / "script.md"
    script.write_text(
        "# Title\n"
        "Shot: a phone in the dark\n"
        "It's late at night. You scroll.\n"
        "Clip: Krishna blesses Arjuna on the chariot\n"
        "Krishna speaks softly.\n"
        "Sfx: bell\n[beat]\n"
        "Stay on your road.\n")
    narration, beats = pipeline._script_beats(script)
    assert narration == "It's late at night. You scroll. Krishna speaks softly. Stay on your road."
    assert [b["kind"] for b in beats] == ["still", "clip"]
    assert beats[0]["prompt"] == "a phone in the dark"
    assert beats[1]["prompt"] == "Krishna blesses Arjuna on the chariot"
    # beat 0 covers "It's late at night. You scroll." (6 words)
    assert beats[0]["words"] == 6
    # beat 1 covers "Krishna speaks softly." + "Stay on your road." (3 + 4 = 7)
    assert beats[1]["words"] == 7


def test_render_requires_script_gate(tmp_path):
    _seed(tmp_path, "script_draft", {})  # no script approval
    with pytest.raises(GateError, match="script"):
        pipeline.render_episode(tmp_path, settings=None)


def test_render_runs_all_stages_and_advances(tmp_path, mocker):
    _seed(tmp_path, "script_approved", {"script": "2026-06-25T10:00:00"})
    # _build_hybrid_segments reads s.fal_key; provide it on the settings mock.
    mocker.patch("studio.pipeline.load_settings", return_value=mocker.Mock(fal_key=""))
    mocker.patch("studio.pipeline.tts.synthesize",
                 return_value=mocker.Mock(usage={"characters": 5}))
    mocker.patch("studio.pipeline.images.generate",
                 return_value=mocker.Mock(usage={"images": 2}))
    mocker.patch("studio.pipeline.music.compose",
                 return_value=mocker.Mock(usage={"tracks": 1}))
    mocker.patch("studio.pipeline.captions.transcribe")
    mocker.patch("studio.pipeline._voiceover_seconds", return_value=20.0)
    mocker.patch("studio.pipeline._image_files",
                 return_value=[tmp_path / "shots" / "00.png", tmp_path / "shots" / "01.png"])
    mocker.patch("studio.pipeline._loop_audio", return_value=tmp_path / "music_full.wav")
    mocker.patch("studio.pipeline._normalize_audio", return_value=tmp_path / "voiceover_norm.wav")
    mocker.patch("studio.pipeline._concat_bookends", return_value=tmp_path / "video.mp4")
    mocker.patch("studio.pipeline.assemble.render_hybrid")
    mocker.patch("studio.pipeline.thumbnail.compose")
    pipeline.render_episode(tmp_path, settings=None)
    st = EpisodeState.load(tmp_path)
    assert st.stage == Stage.RENDER_REVIEW
    assert any(u["stage"] == "tts" for u in st.data["usage"])


def test_build_hybrid_segments_caps_clip_beats(tmp_path, mocker):
    """Scripts may mark many beats as Clip:, but we animate only the first N (per
    FAL_MAX_CLIPS_PER_EP) — extras become Ken-Burns stills to keep the per-episode
    fal spend under control. The cap is the budget guardrail."""
    beats = [
        {"kind": "still", "prompt": "a", "words": 2},
        {"kind": "clip",  "prompt": "b", "words": 2},
        {"kind": "clip",  "prompt": "c", "words": 2},
        {"kind": "clip",  "prompt": "d", "words": 2},
        {"kind": "still", "prompt": "e", "words": 2},
        {"kind": "clip",  "prompt": "f", "words": 2},  # over the cap -> still
        {"kind": "clip",  "prompt": "g", "words": 2},  # over the cap -> still
    ]
    stills = [tmp_path / f"{i:02d}.png" for i in range(len(beats))]
    animate = mocker.patch("studio.pipeline.video_clips.animate",
                           side_effect=lambda *a, **kw: a[3])  # out_path (positional)
    segs = pipeline._build_hybrid_segments(
        beats, stills=stills, total_seconds=14.0, fal_key="fal-key",
        clips_dir=tmp_path / "clips", cap=3)
    # First 3 Clip: beats animated; the rest demoted to stills.
    assert [s["kind"] for s in segs] == [
        "still", "clip", "clip", "clip", "still", "still", "still"
    ]
    # fal was called exactly 3 times — the cap, not the script's clip count.
    assert animate.call_count == 3


def test_build_hybrid_segments_no_fal_key_demotes_all_clips(tmp_path):
    """No fal_key configured (cheap episode) -> every Clip: beat falls back to a
    Ken-Burns still. Animation is purely opt-in."""
    beats = [
        {"kind": "clip", "prompt": "a", "words": 3},
        {"kind": "clip", "prompt": "b", "words": 3},
    ]
    stills = [tmp_path / f"{i:02d}.png" for i in range(len(beats))]
    segs = pipeline._build_hybrid_segments(
        beats, stills=stills, total_seconds=6.0, fal_key="",
        clips_dir=tmp_path / "clips", cap=5)
    assert [s["kind"] for s in segs] == ["still", "still"]


def test_publish_requires_video_gate(tmp_path):
    _seed(tmp_path, "render_review", {"script": "t"})  # no video approval
    with pytest.raises(GateError, match="video"):
        pipeline.publish_episode(tmp_path, settings=None)


def test_publish_uploads_and_advances(tmp_path, mocker):
    _seed(tmp_path, "approved", {"script": "t", "video": "t"})
    (tmp_path / "metadata.json").write_text(json.dumps(
        {"title": "T", "description": "D", "tags": []}))
    (tmp_path / "video.mp4").write_bytes(b"v")
    (tmp_path / "thumb.png").write_bytes(b"t")
    mocker.patch("studio.pipeline.load_settings", return_value=mocker.Mock(
        youtube_client_secret="cs", youtube_token="tok"))
    mocker.patch("studio.pipeline.upload.upload", return_value="VIDEOID123")
    vid = pipeline.publish_episode(tmp_path, settings=None)
    assert vid == "VIDEOID123"
    assert EpisodeState.load(tmp_path).stage == Stage.PUBLISHED


def test_approve_script_records_gate_and_advances(tmp_path):
    _seed(tmp_path, "script_draft", {"topic": "t"})
    pipeline.approve_episode(tmp_path, "script")
    st = EpisodeState.load(tmp_path)
    assert "script" in st.data["approvals"]
    assert st.stage == Stage.SCRIPT_APPROVED


def test_approve_video_records_gate_and_advances(tmp_path):
    _seed(tmp_path, "render_review", {"topic": "t", "script": "t"})
    pipeline.approve_episode(tmp_path, "video")
    st = EpisodeState.load(tmp_path)
    assert "video" in st.data["approvals"]
    assert st.stage == Stage.APPROVED


def test_approve_rejects_unknown_gate(tmp_path):
    _seed(tmp_path, "script_draft", {})
    with pytest.raises(ValueError, match="gate"):
        pipeline.approve_episode(tmp_path, "bogus")


def test_approve_cli_invokes_engine(tmp_path):
    _seed(tmp_path, "script_draft", {"topic": "t"})
    pipeline.main(["approve", str(tmp_path), "--gate", "script"])
    assert "script" in EpisodeState.load(tmp_path).data["approvals"]
