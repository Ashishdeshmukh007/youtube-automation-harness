from pathlib import Path
from studio.config import Settings
from studio import music
from studio.providers import minimax


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


def test_music_request_default_lyrics_is_nonempty():
    """Regression: MiniMax rejects empty lyrics with status 2013.
    The default in music_request must be a non-empty string so callers
    who don't pass lyrics still get a successful instrumental generation.
    """
    url, headers, payload = minimax.music_request(_settings(), "ambient pad")
    assert payload["lyrics"] != "", "music_request must not send empty lyrics"
    assert len(payload["lyrics"]) > 0


def test_music_uses_longer_timeout_than_post_json():
    """Regression: music_generation takes ~2 minutes; default 120s timeout
    in post_json was too short. compose() must use post_music() instead.
    """
    assert minimax._MUSIC_TIMEOUT > 120, "music timeout must exceed default 120s"
