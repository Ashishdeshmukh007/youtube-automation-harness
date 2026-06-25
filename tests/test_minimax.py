from studio.config import Settings
from studio.providers import minimax


def _settings():
    return Settings(
        minimax_api_key="sk-test", minimax_host="https://api.minimax.io",
        minimax_group_id="grp1", voice_id="stoic_male",
        tts_model="speech-2.8-hd", image_model="image-01", music_model="music-2.6",
        youtube_client_secret="x", youtube_token="y",
    )


def test_tts_request_shape():
    url, headers, payload = minimax.tts_request(_settings(), "Hello world")
    assert url == "https://api.minimax.io/v1/t2a_v2?GroupId=grp1"
    assert headers["Authorization"] == "Bearer sk-test"
    assert payload["model"] == "speech-2.8-hd"
    assert payload["text"] == "Hello world"
    assert payload["voice_setting"]["voice_id"] == "stoic_male"


def test_image_request_shape():
    url, headers, payload = minimax.image_request(_settings(), "a marble statue", n=3)
    assert url == "https://api.minimax.io/v1/image_generation"
    assert payload["model"] == "image-01"
    assert payload["prompt"] == "a marble statue"
    assert payload["n"] == 3


def test_music_request_shape():
    url, headers, payload = minimax.music_request(_settings(), "calm ambient", lyrics="")
    assert url == "https://api.minimax.io/v1/music_generation"
    assert payload["model"] == "music-2.6"
    assert payload["prompt"] == "calm ambient"
