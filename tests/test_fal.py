from studio.providers import fal


def test_i2v_request_shape():
    url, headers, payload = fal.i2v_request(
        "fal-key-123", "data:image/jpeg;base64,AAAA", "slow push-in")
    assert url == "https://queue.fal.run/fal-ai/wan/v2.2-a14b/image-to-video"
    assert headers["Authorization"] == "Key fal-key-123"
    assert payload["image_url"].startswith("data:image/jpeg;base64,")
    assert payload["prompt"] == "slow push-in"
    # input safety checker off (false-positives on devotional/battlefield art)
    assert payload["enable_safety_checker"] is False


def test_i2v_request_custom_model():
    url, _, _ = fal.i2v_request("k", "img", "p", model="fal-ai/other/i2v")
    assert url == "https://queue.fal.run/fal-ai/other/i2v"


def test_result_video_url_extracts_nested_url():
    assert fal.result_video_url({"video": {"url": "http://x/c.mp4"}}) == "http://x/c.mp4"
    assert fal.result_video_url({}) is None
