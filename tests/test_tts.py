from pathlib import Path
from studio.config import Settings
from studio import tts


def _settings():
    return Settings("sk", "https://api.minimax.io", "grp", "v", "speech-2.8-hd",
                    "image-01", "music-2.6", "x", "y")


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
