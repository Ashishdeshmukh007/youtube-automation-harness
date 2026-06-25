from pathlib import Path
from studio import sound_fx


def test_parse_script_plain_name():
    text = "Some narration.\nSfx: phone-ring\nMore narration."
    events = sound_fx.parse_script(text)
    assert events == [{"name": "phone-ring", "offset_s": 0.0}]


def test_parse_script_with_offset():
    text = "Sfx: bell at 12.5s"
    events = sound_fx.parse_script(text)
    assert events == [{"name": "bell", "offset_s": 12.5}]


def test_parse_script_no_events():
    text = "No sound here.\nJust narration."
    assert sound_fx.parse_script(text) == []


def test_parse_script_multiple_events():
    text = """Some narration.
Sfx: phone-ring
More.
Sfx: bell at 30s
Sfx: wind at 45.5s"""
    events = sound_fx.parse_script(text)
    assert len(events) == 3
    assert events[0]["name"] == "phone-ring"
    assert events[0]["offset_s"] == 0.0
    assert events[1]["name"] == "bell"
    assert events[1]["offset_s"] == 30.0
    assert events[2]["name"] == "wind"
    assert events[2]["offset_s"] == 45.5


def test_parse_script_case_insensitive():
    text = "sfx: phone-ring\nSFX: bell"
    events = sound_fx.parse_script(text)
    assert len(events) == 2


def test_parse_script_ignores_shot_lines():
    text = "Shot: a chariot\nSfx: wind\nNot an sfx: foo"
    events = sound_fx.parse_script(text)
    assert events == [{"name": "wind", "offset_s": 0.0}]


def test_seed_sound_fx_idempotent():
    """Calling seed twice should not raise; the second call is a no-op."""
    written1 = sound_fx.seed_sound_fx()
    # First call may write if files don't exist; second call writes nothing
    written2 = sound_fx.seed_sound_fx()
    assert written2 == [], "second call should not overwrite"


def test_list_available_includes_seeds():
    names = sound_fx.list_available()
    for expected in ["phone-ring", "bell", "wind", "breath", "silence-gap"]:
        assert expected in names, f"{expected} missing from sound-fx dir"


def test_resolve_event_existing():
    path = sound_fx.resolve_event({"name": "phone-ring", "offset_s": 0.0})
    assert path is not None
    assert path.exists()
    assert path.name == "phone-ring.wav"


def test_resolve_event_missing():
    path = sound_fx.resolve_event({"name": "no-such-sound", "offset_s": 0.0})
    assert path is None