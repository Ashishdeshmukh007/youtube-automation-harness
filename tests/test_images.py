import json
from pathlib import Path
from studio.config import Settings
from studio import images


def _settings():
    return Settings("sk", "https://api.minimax.io", "grp", "v", "speech-2.8-hd",
                    "image-01", "music-2.6", "x", "y")


def test_generate_downloads_and_indexes(tmp_path, mocker):
    mocker.patch("studio.providers.minimax.post_json", return_value={
        "data": {"image_urls": ["http://img/0.png"]},
    })
    mocker.patch("studio.images._download", side_effect=lambda url, dest: dest.write_bytes(b"PNG"))
    shots_dir = tmp_path / "shots"
    shots_dir.mkdir()
    result = images.generate(_settings(), ["a marble bust of Marcus Aurelius"], shots_dir)
    files = sorted(shots_dir.glob("*.png"))
    assert len(files) == 1
    assert files[0].read_bytes() == b"PNG"
    index = json.loads((shots_dir / "shots.json").read_text())
    assert index[0]["prompt"] == "a marble bust of Marcus Aurelius"
    assert result.usage["images"] == 1
