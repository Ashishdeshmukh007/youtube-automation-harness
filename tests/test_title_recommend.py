"""Tests for studio.title_recommend."""

import json
from pathlib import Path

import pytest

from studio import title_recommend


def _settings():
    from studio.config import Settings
    return Settings(
        minimax_api_key="sk-test", minimax_host="https://api.minimax.io",
        minimax_group_id="grp1", voice_id="stoic_male",
        tts_model="speech-2.8-hd", image_model="image-01", music_model="music-2.6",
        youtube_client_secret="x", youtube_token="y",
    )


def _meta():
    return {
        "title": "An old cure for anxiety",
        "description": "A short meditation you can do this week.",
        "tags": ["anxiety", "meditation"],
    }


# ----------------------- metadata -----------------------

def test_load_metadata_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        title_recommend._load_metadata(tmp_path)


def test_load_metadata_returns_parsed(tmp_path):
    (tmp_path / "metadata.json").write_text(json.dumps(_meta()))
    assert title_recommend._load_metadata(tmp_path)["title"].startswith("An old")


# ----------------------- niche fetch -----------------------

def test_fetch_niche_titles_sorts_by_views(mocker):
    mocker.patch("studio.providers.youtube_data.get_json", side_effect=[
        {"items": [
            {"id": {"videoId": "v1"}, "snippet": {"title": "low"}},
            {"id": {"videoId": "v2"}, "snippet": {"title": "high"}},
        ]},
        {"items": [
            {"id": "v1", "statistics": {"viewCount": "10"}, "snippet": {"title": "low"}},
            {"id": "v2", "statistics": {"viewCount": "9000"}, "snippet": {"title": "high"}},
        ]},
    ])
    out = title_recommend.fetch_niche_titles("KEY", "anxiety wisdom", max_results=2)
    assert [t["title"] for t in out] == ["high", "low"]


def test_fetch_niche_titles_empty_search(mocker):
    mocker.patch("studio.providers.youtube_data.get_json",
                 return_value={"items": []})
    assert title_recommend.fetch_niche_titles("KEY", "x") == []


# ----------------------- prompt + JSON parsing -----------------------

def test_build_user_prompt_includes_context():
    p = title_recommend._build_user_prompt(
        {"title": "T", "description": "D" * 600},
        [{"title": "n1", "viewCount": 100}],
        n=3, niche_query="anxiety")
    assert "T" in p and "anxiety" in p
    # Description is truncated to 400 chars
    assert len(p) < 2000


def test_extract_json_object_handles_fenced_block():
    text = 'Here is the JSON:\n```json\n{"candidates": []}\n```\nDone.'
    out = title_recommend._extract_json_object(text)
    assert out == {"candidates": []}


def test_extract_json_object_handles_raw_json():
    text = 'Sure! {"candidates": [{"title": "X"}]}'
    assert title_recommend._extract_json_object(text) == {"candidates": [{"title": "X"}]}


def test_extract_json_object_raises_on_no_json():
    with pytest.raises(ValueError, match="could not find JSON"):
        title_recommend._extract_json_object("no json here at all")


# ----------------------- build_recommendation -----------------------

def test_build_recommendation_runs_end_to_end_with_mocks(mocker, tmp_path):
    mocker.patch("studio.title_recommend.fetch_niche_titles",
                 return_value=[{"title": "winning 1", "viewCount": 1000}])
    mocker.patch("studio.providers.minimax.post_chat",
                 return_value=('{"candidates": [{"title": "Stop Anxiety — the cure you missed",'
                               ' "rationale": "uses Stop X template + hooks on the gap",'
                               ' "template": "stop_x"}]}'))

    rec = title_recommend.build_recommendation(
        "KEY", _settings(), _meta(), "anxiety", n=1)
    assert rec.current_title == "An old cure for anxiety"
    assert rec.top_titles_in_niche[0]["title"] == "winning 1"
    assert len(rec.candidates) == 1
    assert rec.candidates[0].template == "stop_x"


def test_build_recommendation_warns_and_continues_without_api_key(mocker, capsys):
    mocker.patch("studio.providers.minimax.post_chat",
                 return_value='{"candidates": []}')
    rec = title_recommend.build_recommendation("", _settings(), _meta(), "x")
    assert rec.top_titles_in_niche == []
    assert "YOUTUBE_API_KEY is empty" in capsys.readouterr().err


# ----------------------- write + CLI -----------------------

def test_write_recommendation_writes_json(tmp_path):
    rec = title_recommend.TitleRecommendation(
        generated_at="2026-06-26T00:00:00+00:00",
        niche_query="anxiety",
        current_title="T",
        top_titles_in_niche=[],
        candidates=[title_recommend.TitleCandidate(
            title="Stop Anxiety – the cure you missed",
            rationale="uses Stop X + gap",
            template="stop_x")])
    out = title_recommend.write_recommendation(rec, tmp_path)
    assert out == tmp_path / "title-candidates.json"
    data = json.loads(out.read_text())
    assert data["candidates"][0]["template"] == "stop_x"


def test_cli_writes_candidates_and_prints_them(mocker, tmp_path, capsys):
    (tmp_path / "metadata.json").write_text(json.dumps(_meta()))
    mocker.patch("studio.title_recommend.load_settings", return_value=_settings())
    mocker.patch("studio.title_recommend.fetch_niche_titles", return_value=[])
    mocker.patch("studio.providers.minimax.post_chat",
                 return_value='{"candidates": [{"title": "T1", "rationale": "r", "template": "x"},'
                               ' {"title": "T2", "rationale": "r", "template": "y"}]}')

    rc = title_recommend.main([str(tmp_path), "--niche", "anxiety", "-n", "2"])
    assert rc == 0
    out = tmp_path / "title-candidates.json"
    assert out.exists()
    out_text = capsys.readouterr().out
    assert "1. T1" in out_text and "2. T2" in out_text


def test_cli_errors_when_metadata_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        title_recommend.main([str(tmp_path), "--niche", "anxiety"])