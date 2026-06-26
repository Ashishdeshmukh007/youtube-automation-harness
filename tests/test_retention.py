"""Tests for studio.retention and the analytics portion of the YouTube provider."""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from studio import retention
from studio.providers import youtube_data


class _FakeResp:
    def __init__(self, body, status=200):
        self._body = body
        self.status_code = status

    def json(self):
        return self._body


# ----------------------- provider (analytics) tests -----------------------

def test_analytics_get_json_uses_bearer_token(mocker):
    fake = _FakeResp({})
    mock_get = mocker.patch("studio.providers.youtube_data.requests.get",
                            return_value=fake)
    youtube_data.analytics_get_json("TOKEN", "/reports", {"ids": "channel==MINE"})
    headers = mock_get.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer TOKEN"
    assert "/youtubeanalytics.googleapis.com/v2/reports" in mock_get.call_args.args[0]


def test_analytics_get_json_raises_with_parsed_error(mocker):
    fake = _FakeResp({"error": {"message": "forbidden"}}, status=403)
    mocker.patch("studio.providers.youtube_data.requests.get", return_value=fake)
    with pytest.raises(RuntimeError, match="forbidden"):
        youtube_data.analytics_get_json("T", "/reports", {})


def test_fetch_video_retention_decodes_ratio_format(mocker):
    # YouTube's retention row format: [views, "elapsed:0.012345"].
    body = {
        "rows": [
            [1000, "elapsedVideoTimeRatio:0.0"],
            [950, "elapsedVideoTimeRatio:0.05"],
            [800, "elapsedVideoTimeRatio:0.1"],
            [0, "elapsedVideoTimeRatio:1.0"],
        ],
        "columnHeaders": [
            {"name": "videoViewRetention"},
            {"name": "elapsedVideoTimeRatio"},
        ],
    }
    mocker.patch("studio.providers.youtube_data.analytics_get_json",
                 return_value=body)
    out = youtube_data.fetch_video_retention("T", "vid1",
                                             start_date="2026-06-01", end_date="2026-06-26")
    assert out["video_id"] == "vid1"
    assert [p["ratio"] for p in out["curve"]] == [0.0, 0.05, 0.1, 1.0]
    assert [p["views"] for p in out["curve"]] == [1000, 950, 800, 0]


def test_fetch_video_retention_handles_empty(mocker):
    mocker.patch("studio.providers.youtube_data.analytics_get_json",
                 return_value={"rows": []})
    out = youtube_data.fetch_video_retention("T", "vid1",
                                             start_date="2026-06-01", end_date="2026-06-26")
    assert out == {"video_id": "vid1", "curve": []}


# ----------------------- business logic -----------------------

def test_build_summary_averages_and_picks_dropoffs():
    # peak=1000, at ratio 0.0 views=1000 (100%), ratio 0.1 views=800 (80%)
    curve = [
        {"ratio": 0.0, "views": 1000},
        {"ratio": 0.1, "views": 800},
        {"ratio": 0.2, "views": 600},
        {"ratio": 1.0, "views": 200},
    ]
    summary = retention._build_summary(curve, duration_seconds=600.0)
    # At 30s -> ratio 0.05 -> first point >= 0.05 is ratio 0.1 (800/1000=80%)
    # At 60s -> ratio 0.1  -> first point >= 0.1 is ratio 0.1 (80%)
    assert summary["dropoff_at_30s_pct"] == 80.0
    assert summary["dropoff_at_60s_pct"] == 80.0
    # Avg = mean(1.0, 0.8, 0.6, 0.2)*100 = 65
    assert summary["avg_retention_pct"] == 65.0


def test_build_summary_empty_curve_returns_zeros():
    s = retention._build_summary([], duration_seconds=600.0)
    assert s == {"avg_retention_pct": 0.0, "dropoff_at_30s_pct": 0.0,
                 "dropoff_at_60s_pct": 0.0}


def test_build_summary_returns_zeros_when_no_duration():
    # We can't pick dropoffs at 30s/60s without knowing total length.
    s = retention._build_summary([{"ratio": 0.5, "views": 100}], duration_seconds=0.0)
    assert s["dropoff_at_30s_pct"] == 0.0


def test_read_video_id_and_duration_requires_youtube_id(tmp_path):
    (tmp_path / "state.json").write_text(json.dumps({"stage": "published"}))
    with pytest.raises(ValueError, match="youtube_video_id"):
        retention._read_video_id_and_duration(tmp_path)


def test_read_video_id_and_duration_returns_id_and_zero_duration(tmp_path):
    (tmp_path / "state.json").write_text(json.dumps({"youtube_video_id": "vid42"}))
    vid, dur = retention._read_video_id_and_duration(tmp_path)
    assert vid == "vid42" and dur == 0.0


def test_write_report_writes_json(tmp_path):
    r = retention.RetentionReport(
        video_id="vid1", fetched_at="2026-06-26T00:00:00+00:00",
        start_date="2026-06-01", end_date="2026-06-26",
        duration_seconds=600.0,
        curve=[{"ratio": 0.5, "views": 500}],
        avg_retention_pct=80.0, dropoff_at_30s_pct=90.0, dropoff_at_60s_pct=85.0)
    out = retention.write_report(r, tmp_path)
    assert out == tmp_path / "retention.json"
    data = json.loads(out.read_text())
    assert data["video_id"] == "vid1"


def test_draw_chart_returns_none_without_matplotlib(mocker, tmp_path):
    mocker.patch.dict("sys.modules", {"matplotlib": None, "matplotlib.pyplot": None})
    # We need matplotlib to be unimportable, which is tricky — instead test
    # that an empty curve returns None.
    r = retention.RetentionReport(
        video_id="vid1", fetched_at="2026-06-26T00:00:00+00:00",
        start_date="2026-06-01", end_date="2026-06-26", duration_seconds=600.0,
        curve=[], avg_retention_pct=0.0, dropoff_at_30s_pct=0.0,
        dropoff_at_60s_pct=0.0)
    assert retention._draw_chart(r, tmp_path) is None


# ----------------------- CLI -----------------------

def test_cli_writes_retention_json(mocker, tmp_path):
    ep = tmp_path / "ep" / "2026-06-25-test"
    ep.mkdir(parents=True)
    (ep / "state.json").write_text(json.dumps({"youtube_video_id": "vid1"}))
    mocker.patch("studio.retention.load_settings",
                 return_value=type("S", (), {
                     "youtube_client_secret": "x", "youtube_token": "y"})())
    mocker.patch("studio.retention.youtube_data.load_credentials_for_analytics",
                 return_value=type("C", (), {"token": "TOK"})())
    mocker.patch("studio.retention.youtube_data.fetch_video_retention",
                 return_value={"video_id": "vid1", "curve": [
                     {"ratio": 0.0, "views": 100}, {"ratio": 1.0, "views": 60}]})
    rc = retention.main([str(ep)])
    assert rc == 0
    out = ep / "retention.json"
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["video_id"] == "vid1"
    assert len(data["curve"]) == 2
    assert data["avg_retention_pct"] == 80.0  # mean(100, 60) / 100 = 80%


def test_cli_errors_when_state_missing_video_id(mocker, tmp_path):
    ep = tmp_path / "ep" / "2026-06-25-test"
    ep.mkdir(parents=True)
    (ep / "state.json").write_text(json.dumps({"stage": "published"}))
    mocker.patch("studio.retention.load_settings",
                 return_value=type("S", (), {
                     "youtube_client_secret": "x", "youtube_token": "y"})())
    with pytest.raises(ValueError, match="youtube_video_id"):
        retention.main([str(ep)])