from studio.config import Settings
from studio.providers import minimax
import pytest


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


def test_image_request_includes_subject_reference_when_given():
    ref = "data:image/jpeg;base64,AAAA"
    url, headers, payload = minimax.image_request(
        _settings(), "Arjuna at dawn",
        subject_reference=[{"type": "character", "image_file": ref}])
    assert payload["subject_reference"][0]["image_file"] == ref


def test_image_request_omits_subject_reference_when_none():
    url, headers, payload = minimax.image_request(_settings(), "a chariot at dawn")
    assert "subject_reference" not in payload


def test_music_request_shape():
    url, headers, payload = minimax.music_request(_settings(), "calm ambient", lyrics="")
    assert url == "https://api.minimax.io/v1/music_generation"
    assert payload["model"] == "music-2.6"
    assert payload["prompt"] == "calm ambient"


def test_chat_request_shape():
    msgs = [{"role": "user", "content": "hi"}]
    url, _, payload = minimax.chat_request(_settings(), msgs)
    assert url == "https://api.minimax.io/v1/text/chatcompletion_v2"
    assert payload["model"] == "abab6.5s-chat"
    assert payload["messages"] == msgs
    assert payload["temperature"] == 0.7


def test_chat_request_uses_custom_model_and_overrides():
    url, _, payload = minimax.chat_request(
        _settings(), [{"role": "user", "content": "hi"}],
        model="abab6.5-chat", temperature=0.2, max_tokens=200)
    assert payload["model"] == "abab6.5-chat"
    assert payload["temperature"] == 0.2
    assert payload["max_tokens"] == 200


def test_post_chat_extracts_assistant_text(mocker):
    mocker.patch("studio.providers.minimax.post_json",
                 return_value={"choices": [{"message": {"content": "hello"}}]})
    text = minimax.post_chat("u", {}, {})
    assert text == "hello"


def test_post_chat_raises_on_empty_response(mocker):
    mocker.patch("studio.providers.minimax.post_json",
                 return_value={"choices": [{"message": {"content": ""}}]})
    with pytest.raises(RuntimeError, match="empty content"):
        minimax.post_chat("u", {}, {})


def test_post_chat_raises_on_no_choices(mocker):
    mocker.patch("studio.providers.minimax.post_json",
                 return_value={"choices": []})
    with pytest.raises(RuntimeError, match="no choices"):
        minimax.post_chat("u", {}, {})
