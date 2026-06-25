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


def test_render_requires_script_gate(tmp_path):
    _seed(tmp_path, "script_draft", {})  # no script approval
    with pytest.raises(GateError, match="script"):
        pipeline.render_episode(tmp_path, settings=None)


def test_render_runs_all_stages_and_advances(tmp_path, mocker):
    _seed(tmp_path, "script_approved", {"script": "2026-06-25T10:00:00"})
    mocker.patch("studio.pipeline.load_settings", return_value=object())
    mocker.patch("studio.pipeline.tts.synthesize",
                 return_value=mocker.Mock(usage={"characters": 5}))
    mocker.patch("studio.pipeline.images.generate",
                 return_value=mocker.Mock(usage={"images": 2}))
    mocker.patch("studio.pipeline.music.compose",
                 return_value=mocker.Mock(usage={"tracks": 1}))
    mocker.patch("studio.pipeline.captions.transcribe")
    mocker.patch("studio.pipeline._voiceover_seconds", return_value=20.0)
    mocker.patch("studio.pipeline._image_files", return_value=[tmp_path / "shots" / "00.png"])
    mocker.patch("studio.pipeline.cards.render_intro")
    mocker.patch("studio.pipeline.cards.render_outro")
    mocker.patch("studio.pipeline._loop_audio", return_value=tmp_path / "music_full.wav")
    mocker.patch("studio.pipeline._burned_shots_dir", return_value=tmp_path / "shots")
    mocker.patch("studio.pipeline.assemble.render")
    mocker.patch("studio.pipeline.thumbnail.compose")
    pipeline.render_episode(tmp_path, settings=None)
    st = EpisodeState.load(tmp_path)
    assert st.stage == Stage.RENDER_REVIEW
    assert any(u["stage"] == "tts" for u in st.data["usage"])


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
