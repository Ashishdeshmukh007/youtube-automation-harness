from pathlib import Path
from studio.config import Settings
from studio import music


def _settings():
    return Settings("sk", "https://api.minimax.io", "grp", "v", "speech-2.8-hd",
                    "image-01", "music-2.6", "x", "y")


def test_compose_writes_audio(tmp_path, mocker):
    raw = b"RIFFmusic"
    mocker.patch("studio.providers.minimax.post_json", return_value={
        "data": {"audio": raw.hex()},
    })
    out = tmp_path / "music.wav"
    result = music.compose(_settings(), "slow ambient stoic pad, no drums", out)
    assert out.read_bytes() == raw
    assert result.usage["tracks"] == 1
