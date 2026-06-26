"""Tests for studio.calendar."""

import json
from datetime import date
from pathlib import Path

import pytest

from studio import calendar


def _settings():
    from studio.config import Settings
    return Settings(
        minimax_api_key="sk-test", minimax_host="https://api.minimax.io",
        minimax_group_id="grp1", voice_id="stoic_male",
        tts_model="speech-2.8-hd", image_model="image-01", music_model="music-2.6",
        youtube_client_secret="x", youtube_token="y",
    )


# ----------------------- slug + scheduling -----------------------

def test_slugify_uses_date_prefix_and_kebab():
    s = calendar._slugify("Stop Overthinking – Bhagavad Gita's Most Ignored Lesson",
                          date(2026, 7, 6))
    assert s.startswith("2026-07-06-")
    assert "stop-overthinking" in s
    # Slug topic part is truncated to 50 chars (date prefix excluded).
    topic_part = s[len("2026-07-06-"):]
    assert "bhagavad-gita" in topic_part
    assert len(topic_part) <= 50


def test_slugify_handles_empty_and_collapses_dashes():
    assert calendar._slugify("", date(2026, 7, 6)).startswith("2026-07-06-episode")
    assert calendar._slugify("a---b", date(2026, 7, 6)) == "2026-07-06-a-b"


def test_slugify_truncates_to_50_chars_topic_part():
    long = "word " * 30  # 150 chars total
    s = calendar._slugify(long.strip(), date(2026, 7, 6))
    topic_part = s[len("2026-07-06-"):]
    assert len(topic_part) <= 50


def test_schedule_dates_weekly():
    out = calendar._schedule_dates(date(2026, 7, 6), 3, 7)
    assert out == [date(2026, 7, 6), date(2026, 7, 13), date(2026, 7, 20)]


def test_schedule_dates_biweekly():
    out = calendar._schedule_dates(date(2026, 7, 6), 2, 14)
    assert out == [date(2026, 7, 6), date(2026, 7, 20)]


def test_schedule_dates_rejects_zero_or_negative_cadence():
    with pytest.raises(ValueError, match="cadence_days"):
        calendar._schedule_dates(date(2026, 7, 6), 3, 0)
    with pytest.raises(ValueError, match="cadence_days"):
        calendar._schedule_dates(date(2026, 7, 6), 3, -1)


# ----------------------- JSON extraction -----------------------

def test_extract_json_object_handles_fenced_block():
    text = '```json\n{"episodes": []}\n```'
    assert calendar._extract_json_object(text) == {"episodes": []}


def test_extract_json_object_handles_raw_json():
    text = 'Done! {"episodes": [{"working_title": "T"}]}'
    out = calendar._extract_json_object(text)
    assert out["episodes"][0]["working_title"] == "T"


def test_extract_json_object_raises_when_absent():
    with pytest.raises(ValueError, match="could not find JSON"):
        calendar._extract_json_object("no json")


# ----------------------- competitor cross-ref -----------------------

def test_load_competitor_titles_returns_empty_when_no_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert calendar._load_competitor_titles(None) == []


def test_load_competitor_titles_reads_explicit_path(tmp_path):
    rep = tmp_path / "report.json"
    rep.write_text(json.dumps({
        "channels": [
            {"top_videos": [{"title": "A"}, {"title": "B"}]},
            {"top_videos": [{"title": "C"}]},
        ],
    }))
    assert calendar._load_competitor_titles(rep) == ["A", "B", "C"]


def test_load_competitor_titles_auto_picks_latest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rep_dir = tmp_path / "competitor-reports"
    rep_dir.mkdir()
    (rep_dir / "competitors-20260101T000000Z.json").write_text(
        json.dumps({"channels": [{"top_videos": [{"title": "old"}]}]}))
    (rep_dir / "competitors-20260625T000000Z.json").write_text(
        json.dumps({"channels": [{"top_videos": [{"title": "new"}]}]}))
    assert calendar._load_competitor_titles(None) == ["new"]


def test_load_competitor_titles_handles_bad_json(tmp_path):
    rep = tmp_path / "report.json"
    rep.write_text("not json")
    assert calendar._load_competitor_titles(rep) == []


# ----------------------- build_calendar -----------------------

def test_build_calendar_assigns_dates_and_slugs(mocker):
    mocker.patch("studio.providers.minimax.post_chat", return_value=(
        '{"episodes": ['
        '{"working_title": "Stop Overthinking – Bhagavad Gita", '
        ' "topic": "rumination", '
        ' "source_text": "Bhagavad Gita 2.54-2.72", '
        ' "hook_idea": "You check your phone at 3am..."},'
        '{"working_title": "What the Gita knew about anger", '
        ' "topic": "anger", "source_text": "Bhagavad Gita 2.62-2.63", '
        ' "hook_idea": "the email you sent this morning..."}'
        ']}'))
    cal = calendar.build_calendar(
        _settings(), series="What the Gita knew about ___",
        n=2, start=date(2026, 7, 6), cadence_days=7)
    assert cal.series == "What the Gita knew about ___"
    assert len(cal.episodes) == 2
    assert cal.episodes[0].planned_date == "2026-07-06"
    assert cal.episodes[1].planned_date == "2026-07-13"
    assert cal.episodes[0].slug.startswith("2026-07-06-")
    assert cal.episodes[1].slug.startswith("2026-07-13-")
    # Episode numbers are 1-indexed and sequential.
    assert [e.episode_number for e in cal.episodes] == [1, 2]


def test_build_calendar_truncates_extra_episodes(mocker):
    # LLM returned 3 but we asked for 2 — should keep the first 2.
    mocker.patch("studio.providers.minimax.post_chat", return_value=(
        '{"episodes": ['
        '{"working_title":"A","topic":"","source_text":"","hook_idea":""},'
        '{"working_title":"B","topic":"","source_text":"","hook_idea":""},'
        '{"working_title":"C","topic":"","source_text":"","hook_idea":""}'
        ']}'))
    cal = calendar.build_calendar(
        _settings(), series="What the Gita knew about ___",
        n=2, start=date(2026, 7, 6))
    assert len(cal.episodes) == 2


def test_build_calendar_warns_on_unknown_series(mocker, capsys):
    mocker.patch("studio.providers.minimax.post_chat",
                 return_value='{"episodes": []}')
    calendar.build_calendar(_settings(), series="Made-up series name",
                            n=2, start=date(2026, 7, 6))
    err = capsys.readouterr().err
    assert "canonical" in err


# ----------------------- write + CLI -----------------------

def test_write_calendar_writes_dated_json(tmp_path):
    cal = calendar.ContentCalendar(
        generated_at="2026-06-26T00:00:00+00:00",
        series="What the Gita knew about ___",
        start_date="2026-07-06", cadence_days=7,
        episodes=[calendar.CalendarEntry(
            episode_number=1, planned_date="2026-07-06",
            slug="2026-07-06-stop-overthinking", working_title="T",
            topic="x", source_text="y", hook_idea="z")])
    out = calendar.write_calendar(cal, tmp_path)
    assert out.name.startswith("calendar-")
    assert out.name.endswith("-2026-07-06.json")
    data = json.loads(out.read_text())
    assert data["episodes"][0]["slug"] == "2026-07-06-stop-overthinking"


def test_cli_writes_calendar_and_prints_summary(mocker, tmp_path, capsys):
    mocker.patch("studio.calendar.load_settings", return_value=_settings())
    mocker.patch("studio.calendar.build_calendar",
                 return_value=calendar.ContentCalendar(
                     generated_at="2026-06-26T00:00:00+00:00",
                     series="What the Gita knew about ___",
                     start_date="2026-07-06", cadence_days=7,
                     episodes=[calendar.CalendarEntry(
                         episode_number=1, planned_date="2026-07-06",
                         slug="x", working_title="Stop Overthinking",
                         topic="t", source_text="s", hook_idea="h")]))

    rc = calendar.main([
        "--series", "What the Gita knew about ___",
        "--episodes", "1",
        "--start", "2026-07-06",
        "--out", str(tmp_path),
    ])
    assert rc == 0
    files = list(tmp_path.glob("calendar-*.json"))
    assert len(files) == 1
    out = capsys.readouterr().out
    assert "1. [2026-07-06] Stop Overthinking" in out


def test_cli_rejects_bad_date(mocker, tmp_path, capsys):
    mocker.patch("studio.calendar.load_settings", return_value=_settings())
    rc = calendar.main([
        "--series", "What the Gita knew about ___",
        "--start", "not-a-date",
        "--out", str(tmp_path),
    ])
    assert rc == 2
    assert "YYYY-MM-DD" in capsys.readouterr().err