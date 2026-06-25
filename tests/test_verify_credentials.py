from studio.config import Settings
from studio import verify_credentials as vc


def _settings():
    return Settings(
        minimax_api_key="sk-test", minimax_host="https://api.minimax.io",
        minimax_group_id="grp1", voice_id="v", tts_model="speech-2.8-hd",
        image_model="image-01", music_model="music-2.6",
        youtube_client_secret="x", youtube_token="y",
    )


def test_check_endpoint_reports_ok(mocker):
    mocker.patch("studio.providers.minimax.post_json", return_value={"base_resp": {"status_code": 0}})
    result = vc.check_endpoint("tts", _settings())
    assert result["ok"] is True


def test_check_endpoint_reports_failure(mocker):
    mocker.patch("studio.providers.minimax.post_json", side_effect=Exception("401 invalid key"))
    result = vc.check_endpoint("tts", _settings())
    assert result["ok"] is False
    assert "401" in result["error"]
