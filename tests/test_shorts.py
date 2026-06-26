"""Tests for studio.shorts."""

import json
import subprocess
from pathlib import Path

import pytest

from studio import shorts


def _settings():
    from studio.config import Settings
    return Settings(
        minimax_api_key="sk-test", minimax_host="https://api.minimax.io",
        minimax_group_id="grp1", voice_id="stoic_male",
        tts_model="speech-2.8-hd", image_model="image-01", music_model="music-2.6",
        youtube_client_secret="x", youtube_token="y",
    )


# ----------------------- script parsing -----------------------

def test_parse_paragraphs_splits_on_visual_markers(tmp_path):
    script = tmp_path / "script.md"
    script.write_text(
        "# Title\n"
        "Shot: a phone screen at 3am\n"
        "You check the phone before you're awake.\n"
        "By nine you're already behind.\n"
        "Shot: a candle in a still room\n"
        "Twenty-three centuries ago, someone described this exactly.\n"
        "The Yoga Sutras call the whirlpools vrittis.\n"
        "Sfx: bell\n"
        "Tomorrow morning, before the phone, sit ninety seconds.\n"
    )
    paras = shorts.parse_paragraphs(script)
    assert len(paras) == 3
    assert "phone" in paras[0].text
    assert "Twenty-three centuries" in paras[1].text
    assert "Tomorrow morning" in paras[2].text
    # SFX and Shot/Clip lines don't leak into any paragraph.
    assert not any("Sfx" in p.text or "Shot" in p.text or "bell" in p.text
                   for p in paras)


def test_parse_paragraphs_handles_empty_script(tmp_path):
    script = tmp_path / "script.md"
    script.write_text("# Title\nShot: a still\n")
    assert shorts.parse_paragraphs(script) == []


def test_time_paragraphs_assigns_contiguous_windows(tmp_path):
    # 3 paragraphs split by Shot: markers; 2, 4, 1 words respectively.
    script = tmp_path / "script.md"
    script.write_text(
        "Shot: a\nTwo words.\n"
        "Shot: b\nFour words here now.\n"
        "Shot: c\nOne.\n"
    )
    paras = shorts.parse_paragraphs(script)
    assert len(paras) == 3
    timed = shorts.time_paragraphs(paras, voiceover_seconds=14.0)
    # Proportional: 2/7, 4/7, 1/7 of 14s = 4s, 8s, 2s.
    assert timed[0].end_seconds == pytest.approx(4.0)
    assert timed[1].end_seconds == pytest.approx(12.0)
    assert timed[2].end_seconds == pytest.approx(14.0)
    # Windows are contiguous (no gaps).
    assert timed[0].start_seconds == 0.0
    assert timed[1].start_seconds == pytest.approx(4.0)
    assert timed[2].start_seconds == pytest.approx(12.0)


def test_voiceover_seconds_estimates_when_wav_missing(tmp_path):
    script = tmp_path / "script.md"
    # 100 words -> ~38.8s at 2.58 wps.
    script.write_text("word " * 100)
    est = shorts.voiceover_seconds(tmp_path)
    assert 35 < est < 42


def test_voiceover_seconds_uses_ffprobe_when_present(tmp_path, mocker):
    vo = tmp_path / "voiceover.wav"
    vo.write_bytes(b"RIFF")  # just needs to exist
    mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess(
        args=[], returncode=0, stdout="123.45\n", stderr=""))
    assert shorts.voiceover_seconds(tmp_path) == 123.45


# ----------------------- LLM parsing -----------------------

def test_extract_json_object_handles_fenced():
    text = '```json\n{"picks": []}\n```'
    assert shorts._extract_json_object(text) == {"picks": []}


def test_extract_json_object_handles_raw():
    text = '{"picks": [{"paragraph_index": 1}]}'
    assert shorts._extract_json_object(text) == {"picks": [{"paragraph_index": 1}]}


def test_extract_json_object_raises():
    with pytest.raises(ValueError, match="could not find JSON"):
        shorts._extract_json_object("nothing here")


def test_truncate_caption_truncates_at_word_boundary():
    text = "one two three four five six seven eight nine ten eleven twelve"
    out = shorts._truncate_caption(text, max_chars=30)
    assert len(out) <= 31  # 30 + ellipsis
    assert out.endswith("…")


def test_truncate_caption_short_input_unchanged():
    assert shorts._truncate_caption("Short caption.", 80) == "Short caption."


# ----------------------- pick_clips -----------------------

def test_pick_clips_filters_by_length_window(mocker):
    paras = [
        shorts.ScriptParagraph(0, "short", 0.0, 20.0),
        shorts.ScriptParagraph(1, "in window", 20.0, 80.0),
        shorts.ScriptParagraph(2, "also in window", 80.0, 140.0),
        shorts.ScriptParagraph(3, "way too long", 140.0, 300.0),
    ]
    mocker.patch("studio.providers.minimax.post_chat", return_value=(
        '{"picks": ['
        '{"paragraph_index": 0, "rationale": "too short", "caption": "x"},'
        '{"paragraph_index": 1, "rationale": "good", "caption": "y"},'
        '{"paragraph_index": 2, "rationale": "good", "caption": "z"},'
        '{"paragraph_index": 3, "rationale": "too long", "caption": "w"}'
        ']}'))
    picks = shorts.pick_clips(_settings(), paras, n=4, min_seconds=45.0,
                              max_seconds=75.0)
    assert [p.paragraph_index for p in picks] == [1, 2]


def test_pick_clips_dedupes_duplicate_paragraph_indices(mocker):
    paras = [
        shorts.ScriptParagraph(0, "in window a", 0.0, 60.0),
        shorts.ScriptParagraph(1, "in window b", 60.0, 120.0),
    ]
    # LLM returns the same paragraph twice.
    mocker.patch("studio.providers.minimax.post_chat", return_value=(
        '{"picks": ['
        '{"paragraph_index": 0, "rationale": "r", "caption": "a"},'
        '{"paragraph_index": 0, "rationale": "dup", "caption": "again"}'
        ']}'))
    picks = shorts.pick_clips(_settings(), paras, n=2)
    assert len(picks) == 1
    assert picks[0].paragraph_index == 0


def test_pick_clips_ignores_unknown_indices(mocker):
    paras = [shorts.ScriptParagraph(0, "in window", 0.0, 60.0)]
    mocker.patch("studio.providers.minimax.post_chat", return_value=(
        '{"picks": ['
        '{"paragraph_index": 99, "rationale": "r", "caption": "x"},'
        '{"paragraph_index": 0, "rationale": "r", "caption": "y"}'
        ']}'))
    picks = shorts.pick_clips(_settings(), paras, n=2)
    assert [p.paragraph_index for p in picks] == [0]


def test_pick_clips_truncates_captions(mocker):
    paras = [shorts.ScriptParagraph(0, "in window", 0.0, 60.0)]
    long_caption = "word " * 30
    mocker.patch("studio.providers.minimax.post_chat", return_value=(
        f'{{"picks": [{{"paragraph_index": 0, "rationale": "r", "caption": "{long_caption}"}}]}}'))
    picks = shorts.pick_clips(_settings(), paras, n=1)
    assert len(picks[0].caption) <= 81  # 80 + ellipsis


# ----------------------- caption overlay -----------------------

def test_render_caption_overlay_writes_png(tmp_path):
    out = shorts.render_caption_overlay("Hello world", 60.0, tmp_path / "cap.png")
    assert out.exists()
    assert out.suffix == ".png"
    # PNG is the right size.
    from PIL import Image
    img = Image.open(out)
    assert img.size == (1080, 1920)


def test_render_caption_overlay_wraps_long_lines(tmp_path):
    long_caption = "word " * 40  # forces wrapping
    shorts.render_caption_overlay(long_caption, 60.0, tmp_path / "cap.png")
    assert (tmp_path / "cap.png").exists()


# ----------------------- ffmpeg render -----------------------

def test_render_short_calls_ffmpeg_with_music(mocker, tmp_path):
    src = tmp_path / "src.mp4"
    src.write_bytes(b"\x00")  # existence is what render checks
    caption = tmp_path / "cap.png"
    caption.write_bytes(b"\x89PNG\r\n\x1a\n")
    out = tmp_path / "out.mp4"
    music = tmp_path / "music.wav"
    music.write_bytes(b"RIFF")

    mock_run = mocker.patch("studio.shorts.subprocess.run")
    shorts.render_short(
        shorts.ShortPick(paragraph_index=0, text="t",
                         start_seconds=10.0, end_seconds=70.0,
                         rationale="r", caption="c"),
        source_video=src, out_path=out, caption_png=caption, music_path=music)
    cmd = mock_run.call_args.args[0]
    # Music present -> caption index = 2, music index = 1.
    assert any("music.wav" in str(c) for c in cmd)
    # filter_complex is the arg immediately after the literal "-filter_complex".
    fc_idx = cmd.index("-filter_complex") + 1
    fc = cmd[fc_idx]
    assert "[vsrc][2:v]overlay" in fc
    assert "[1:a]" in fc
    assert "amix=inputs=2" in fc


def test_render_short_omits_music_when_path_missing(mocker, tmp_path):
    src = tmp_path / "src.mp4"
    src.write_bytes(b"\x00")
    caption = tmp_path / "cap.png"
    caption.write_bytes(b"\x89PNG\r\n\x1a\n")
    out = tmp_path / "out.mp4"

    mock_run = mocker.patch("studio.shorts.subprocess.run")
    shorts.render_short(
        shorts.ShortPick(paragraph_index=0, text="t",
                         start_seconds=10.0, end_seconds=70.0,
                         rationale="r", caption="c"),
        source_video=src, out_path=out, caption_png=caption, music_path=None)
    cmd = mock_run.call_args.args[0]
    fc_idx = cmd.index("-filter_complex") + 1
    fc = cmd[fc_idx]
    # No music -> caption index = 1.
    assert "[vsrc][1:v]overlay" in fc
    assert "amix=inputs=1" in fc


# ----------------------- top-level extract -----------------------

def test_extract_writes_shorts_json_and_mp4s(mocker, tmp_path):
    ep = tmp_path / "2026-07-06-test"
    ep.mkdir()
    (ep / "script.md").write_text(
        "Shot: a phone at 3am\n"
        "You check the phone before you're awake. " * 5 + "\n"  # ~25 words
        "Shot: a candle\n"
        "Twenty-three centuries ago, someone described this exactly. " * 8 + "\n"
        "Shot: dawn\n"
        "Tomorrow morning, sit ninety seconds. " * 3 + "\n"
    )
    (ep / "voiceover.wav").write_bytes(b"RIFF")
    (ep / "video.mp4").write_bytes(b"\x00")

    mocker.patch("studio.shorts.voiceover_seconds", return_value=100.0)
    mocker.patch("studio.shorts.pick_clips", return_value=[
        shorts.ShortPick(paragraph_index=1, text="x",
                         start_seconds=25.0, end_seconds=80.0,
                         rationale="r", caption="Hello")])
    mocker.patch("studio.shorts.render_caption_overlay",
                 side_effect=lambda c, d, p: p)

    def _fake_render(pick, **kw):
        kw["out_path"].write_bytes(b"\x00")
        return kw["out_path"]
    mocker.patch("studio.shorts.render_short", side_effect=_fake_render)

    out = shorts.extract(ep, n=1)
    assert len(out.rendered) == 1
    assert Path(out.rendered[0]).exists()
    data = json.loads((ep / "shorts.json").read_text())
    assert data["slug"] == ep.name
    assert data["picks"][0]["paragraph_index"] == 1


def test_extract_errors_when_no_picks_fit_window(mocker, tmp_path):
    ep = tmp_path / "2026-07-06-test"
    ep.mkdir()
    (ep / "script.md").write_text("Shot: a\nFirst short paragraph.\n")
    (ep / "video.mp4").write_bytes(b"\x00")

    mocker.patch("studio.shorts.voiceover_seconds", return_value=10.0)
    mocker.patch("studio.shorts.pick_clips", return_value=[])
    with pytest.raises(RuntimeError, match="no passages fit"):
        shorts.extract(ep, n=1)


def test_extract_errors_when_inputs_missing(tmp_path):
    ep = tmp_path / "2026-07-06-test"
    ep.mkdir()
    with pytest.raises(FileNotFoundError, match="script.md"):
        shorts.extract(ep)
    (ep / "script.md").write_text("text\n")
    with pytest.raises(FileNotFoundError, match="video.mp4"):
        shorts.extract(ep)


# ----------------------- CLI -----------------------

def test_cli_runs_and_reports(mocker, tmp_path, capsys):
    ep = tmp_path / "2026-07-06-test"
    ep.mkdir()
    mocker.patch("studio.shorts.extract", return_value=shorts.ShortsOutput(
        slug="2026-07-06-test", source_video="x", generated_at="now",
        rendered=[str(ep / "shorts" / "01.mp4")]))
    rc = shorts.main([str(ep), "-n", "1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "01.mp4" in out