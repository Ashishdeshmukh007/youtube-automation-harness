import json
from pathlib import Path
from studio.config import Settings
from studio import images
from studio.providers import minimax


def _settings():
    return Settings("sk", "https://api.minimax.io", "grp", "v", "speech-2.8-hd",
                    "image-01", "music-2.6", "x", "y")


def _mock_api(mocker):
    mocker.patch("studio.providers.minimax.post_json", return_value={
        "data": {"image_urls": ["http://img/0.png"]},
    })
    mocker.patch("studio.images._download",
                 side_effect=lambda url, dest: dest.write_bytes(b"PNG"))


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


def test_generate_attaches_subject_reference_for_character(tmp_path, mocker):
    _mock_api(mocker)
    spy = mocker.spy(minimax, "image_request")
    shots_dir = tmp_path / "shots"
    shots_dir.mkdir()
    images.generate(_settings(), ["Arjuna kneeling on a chariot at dawn"], shots_dir)
    subj = spy.call_args.kwargs.get("subject_reference")
    assert subj is not None, "a named character should attach a subject_reference"
    assert subj[0]["image_file"].startswith("data:image/jpeg;base64,")


def test_generate_no_subject_reference_for_plain_prompt(tmp_path, mocker):
    _mock_api(mocker)
    spy = mocker.spy(minimax, "image_request")
    shots_dir = tmp_path / "shots"
    shots_dir.mkdir()
    images.generate(_settings(), ["a still pool of water at dawn, no people"], shots_dir)
    assert spy.call_args.kwargs.get("subject_reference") is None
