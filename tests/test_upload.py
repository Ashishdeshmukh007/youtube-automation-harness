from studio.upload import build_body


def test_build_body_defaults_to_private():
    meta = {"title": "Amor Fati", "description": "On loving fate",
            "tags": ["stoicism", "philosophy"]}
    body = build_body(meta)
    assert body["snippet"]["title"] == "Amor Fati"
    assert body["snippet"]["tags"] == ["stoicism", "philosophy"]
    assert body["status"]["privacyStatus"] == "private"


def test_build_body_respects_visibility_and_schedule():
    meta = {"title": "T", "description": "D", "tags": [],
            "visibility": "public", "publish_at": "2026-07-01T12:00:00Z"}
    body = build_body(meta)
    assert body["status"]["privacyStatus"] == "public"
    assert body["status"]["publishAt"] == "2026-07-01T12:00:00Z"
