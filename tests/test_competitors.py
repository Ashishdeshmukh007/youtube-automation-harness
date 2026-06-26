"""Tests for studio.competitors and studio.providers.youtube_data.

Both modules are exercised end-to-end with mocked HTTP responses, so we can
verify the request shape, response parsing, and CLI behavior without
hitting the real API.
"""

import json
from pathlib import Path

import pytest

from studio import competitors
from studio.providers import youtube_data


# ----------------------------- provider tests -----------------------------

class _FakeResp:
    def __init__(self, body, status=200):
        self._body = body
        self.status_code = status

    def json(self):
        if isinstance(self._body, (bytes, bytearray)):
            return json.loads(self._body.decode())
        return self._body

    @property
    def text(self):
        return json.dumps(self._body)


def test_get_json_attaches_api_key(mocker):
    fake = _FakeResp({"items": []})
    mock_get = mocker.patch("studio.providers.youtube_data.requests.get",
                            return_value=fake)
    youtube_data.get_json("KEY123", "/search", {"q": "test"})
    called_url = mock_get.call_args.args[0]
    assert "key=KEY123" in called_url
    assert "/youtube/v3/search" in called_url


def test_get_json_raises_with_parsed_error_body_on_4xx(mocker):
    fake = _FakeResp({"error": {"message": "quota exceeded"}}, status=403)
    mocker.patch("studio.providers.youtube_data.requests.get", return_value=fake)
    with pytest.raises(RuntimeError, match="quota exceeded"):
        youtube_data.get_json("KEY", "/search", {})


def test_resolve_handle_extracts_channel_id(mocker):
    mocker.patch("studio.providers.youtube_data.get_json",
                 return_value={"items": [{"id": "UC123"}]})
    assert youtube_data.resolve_handle("KEY", "@AnimatedGita") == "UC123"


def test_resolve_handle_raises_when_not_found(mocker):
    mocker.patch("studio.providers.youtube_data.get_json",
                 return_value={"items": []})
    with pytest.raises(LookupError):
        youtube_data.resolve_handle("KEY", "@nope")


def test_search_channels_maps_response(mocker):
    mocker.patch("studio.providers.youtube_data.get_json", return_value={
        "items": [{"id": {"channelId": "UC1"}, "snippet": {"title": "A"}}]})
    out = youtube_data.search_channels("KEY", "gita", max_results=10)
    assert out == [{"id": "UC1", "title": "A", "description": ""}]


def test_channel_stats_parses_counts(mocker):
    mocker.patch("studio.providers.youtube_data.get_json", return_value={
        "items": [{
            "id": "UC1",
            "statistics": {"subscriberCount": "1000", "viewCount": "50000",
                           "videoCount": "20"},
            "snippet": {"title": "Chan", "thumbnails": {"default": {"url": "t"}}},
        }]})
    s = youtube_data.channel_stats("KEY", "UC1")
    assert s["subscribers"] == 1000 and s["viewCount"] == 50000


def test_channel_stats_batch_handles_missing_thumbnails(mocker):
    mocker.patch("studio.providers.youtube_data.get_json", return_value={
        "items": [{
            "id": "UC1",
            "statistics": {"subscriberCount": "5"},
            "snippet": {"title": "Chan"},
        }]})
    out = youtube_data.channel_stats_batch("KEY", ["UC1"])
    assert out[0]["subscribers"] == 5 and out[0]["thumbnail_url"] == ""


def test_top_videos_sorts_by_views_and_joins_stats(mocker):
    # search returns two ids; stats body has actual view counts.
    responses = iter([
        {"items": [
            {"id": {"videoId": "v1"}, "snippet": {"title": "low"}},
            {"id": {"videoId": "v2"}, "snippet": {"title": "high"}},
        ]},
        {"items": [
            {"id": "v1", "statistics": {"viewCount": "10"}, "snippet": {"title": "low"}},
            {"id": "v2", "statistics": {"viewCount": "9999"}, "snippet": {"title": "high"}},
        ]},
    ])
    mocker.patch("studio.providers.youtube_data.get_json",
                 side_effect=lambda *a, **kw: next(responses))
    out = youtube_data.top_videos_for_channel("KEY", "UC1", max_results=2)
    assert [v["id"] for v in out] == ["v2", "v1"]


# ----------------------------- business logic -----------------------------

def test_build_report_rejects_both_query_and_seed():
    with pytest.raises(ValueError, match="not both"):
        competitors.build_report("KEY", query="q", seed_handles=["@a"],
                                 max_channels=5, top_videos=3)


def test_build_report_rejects_neither_query_nor_seed():
    with pytest.raises(ValueError, match="provide either"):
        competitors.build_report("KEY", query=None, seed_handles=[],
                                 max_channels=5, top_videos=3)


def test_build_report_query_path(mocker):
    # search → 2 seeds; channel_stats_batch → 2 with viewCount; top_videos → empty
    mocker.patch("studio.providers.youtube_data.search_channels",
                 return_value=[{"id": "UC1", "title": "A"},
                               {"id": "UC2", "title": "B"}])
    mocker.patch("studio.providers.youtube_data.channel_stats_batch",
                 return_value=[{"id": "UC1", "title": "A", "subscribers": 100,
                                "viewCount": 500, "videoCount": 5, "thumbnail_url": ""},
                               {"id": "UC2", "title": "B", "subscribers": 50,
                                "viewCount": 9000, "videoCount": 3, "thumbnail_url": ""}])
    mocker.patch("studio.providers.youtube_data.top_videos_for_channel", return_value=[])

    r = competitors.build_report("KEY", query="gita", seed_handles=[],
                                 max_channels=5, top_videos=3)
    # sorted by viewCount desc
    assert [c.id for c in r.channels] == ["UC2", "UC1"]
    assert r.query == "gita" and r.seed_handles == []


def test_build_report_seed_path_skips_missing_handles(mocker, capsys):
    mocker.patch("studio.providers.youtube_data.resolve_handle",
                 side_effect=[LookupError("nope"), "UC1"])
    mocker.patch("studio.providers.youtube_data.channel_stats_batch",
                 return_value=[{"id": "UC1", "title": "A", "subscribers": 1,
                                "viewCount": 1, "videoCount": 1, "thumbnail_url": ""}])
    mocker.patch("studio.providers.youtube_data.top_videos_for_channel", return_value=[])
    r = competitors.build_report("KEY", query=None,
                                 seed_handles=["@missing", "@ok"],
                                 max_channels=5, top_videos=3)
    assert [c.id for c in r.channels] == ["UC1"]
    assert "skip" in capsys.readouterr().err


def test_attach_top_videos_swallows_per_channel_errors(mocker, capsys):
    ch = competitors.CompetitorChannel(
        id="UC1", title="A", subscribers=1, viewCount=1,
        videoCount=1, thumbnail_url="")
    mocker.patch("studio.providers.youtube_data.top_videos_for_channel",
                 side_effect=RuntimeError("boom"))
    competitors.attach_top_videos("KEY", [ch], top_videos=3)
    assert ch.top_videos == []
    assert "boom" in capsys.readouterr().err


def test_write_report_writes_timestamped_json(tmp_path):
    r = competitors.CompetitorReport(
        generated_at="2026-06-26T00:00:00+00:00",
        query="gita", seed_handles=[],
        channels=[competitors.CompetitorChannel(
            id="UC1", title="A", subscribers=1, viewCount=1, videoCount=1,
            thumbnail_url="",
            top_videos=[competitors.CompetitorVideo(
                id="v1", title="t", viewCount=10, likeCount=1,
                commentCount=0, publishedAt="2026-01-01T00:00:00Z",
                thumbnail_url="")])])
    out = competitors.write_report(r, tmp_path)
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["channels"][0]["top_videos"][0]["viewCount"] == 10
    assert out.name.startswith("competitors-")
    assert out.name.endswith(".json")


# ----------------------------- CLI tests -----------------------------

def test_cli_writes_report_and_exits_0(mocker, tmp_path, monkeypatch):
    mocker.patch("studio.competitors.load_settings",
                 return_value=type("S", (), {"youtube_api_key": "KEY"})())
    mocker.patch("studio.competitors.build_report",
                 return_value=competitors.CompetitorReport(
                     generated_at="2026-06-26T00:00:00+00:00",
                     query="gita", seed_handles=[],
                     channels=[competitors.CompetitorChannel(
                         id="UC1", title="A", subscribers=1, viewCount=1,
                         videoCount=1, thumbnail_url="")]))

    rc = competitors.main(["--query", "gita", "--out", str(tmp_path)])
    assert rc == 0
    files = list(tmp_path.glob("competitors-*.json"))
    assert len(files) == 1


def test_cli_fails_when_api_key_missing(mocker, monkeypatch):
    mocker.patch("studio.competitors.load_settings",
                 return_value=type("S", (), {"youtube_api_key": ""})())
    rc = competitors.main(["--query", "gita"])
    assert rc == 2


def test_cli_requires_query_or_seed(capsys):
    # argparse exits with SystemExit(2) when the mutually-exclusive group is empty
    with pytest.raises(SystemExit):
        competitors.main([])