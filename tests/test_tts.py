from pathlib import Path
from studio.config import Settings
from studio import tts


def _settings():
    return Settings("sk", "https://api.minimax.io", "grp", "v", "speech-2.8-hd",
                    "image-01", "music-2.6", "x", "y")


def test_synthesize_respells_sanskrit_before_tts(tmp_path, mocker):
    """The text sent to MiniMax should have Sanskrit terms phonetically respelled."""
    spy = mocker.spy(tts.minimax, "tts_request")
    mocker.patch("studio.providers.minimax.post_json", return_value={
        "data": {"audio": b"x".hex()}})
    tts.synthesize(_settings(), "the dharma of Arjuna", tmp_path / "v.wav")
    sent_text = spy.call_args.args[1]
    assert "dharma" not in sent_text
    assert "Arjuna" not in sent_text


def test_synthesize_writes_decoded_audio(tmp_path, mocker):
    fake_bytes = b"RIFFfakewav"
    mocker.patch("studio.providers.minimax.post_json", return_value={
        "data": {"audio": fake_bytes.hex()},
        "extra_info": {"audio_length": 1000},
    })
    out = tmp_path / "voiceover.wav"
    result = tts.synthesize(_settings(), "Hello", out)
    assert out.read_bytes() == fake_bytes
    assert result.path == out
    assert result.usage["characters"] == len("Hello")
