from studio import video_clips


def test_animate_submits_polls_and_downloads(tmp_path, mocker):
    mocker.patch("studio.video_clips._data_uri", return_value="data:image/jpeg;base64,AA")
    submit = mocker.patch("studio.providers.fal.submit",
                          return_value={"status_url": "s", "response_url": "r"})
    mocker.patch("studio.providers.fal.poll_until_done")
    mocker.patch("studio.providers.fal.get_result",
                 return_value={"video": {"url": "http://v/c.mp4"}})
    mocker.patch("studio.video_clips._download",
                 side_effect=lambda url, dest: dest.write_bytes(b"MP4"))
    out = video_clips.animate("fal-key", tmp_path / "still.png", "slow push-in",
                              tmp_path / "clip.mp4")
    assert out.read_bytes() == b"MP4"
    # the still + prompt were sent to fal
    _, _, payload = submit.call_args.args
    assert payload["prompt"] == "slow push-in"


def test_animate_raises_when_no_video_url(tmp_path, mocker):
    mocker.patch("studio.video_clips._data_uri", return_value="data:image/jpeg;base64,AA")
    mocker.patch("studio.providers.fal.submit",
                 return_value={"status_url": "s", "response_url": "r"})
    mocker.patch("studio.providers.fal.poll_until_done")
    mocker.patch("studio.providers.fal.get_result", return_value={})
    import pytest
    with pytest.raises(RuntimeError):
        video_clips.animate("k", tmp_path / "s.png", "p", tmp_path / "c.mp4")
