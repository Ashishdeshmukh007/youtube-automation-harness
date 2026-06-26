from studio import visual_style, characters


def setup_function(_):
    visual_style.reset_cache()
    characters.reset_cache()


def test_apply_brand_style_appends_palette():
    prompt = "a phone screen glowing in a dark bedroom"
    out = visual_style.apply_brand_style(prompt)
    assert prompt in out
    assert "Cinematic film still" in out
    assert "rich warm cinematic color" in out


def test_apply_brand_style_forbidden_list_present():
    prompt = "a chariot on a riverbank at twilight"
    out = visual_style.apply_brand_style(prompt)
    for forbidden in ["only Indian / South Asian people", "no neon", "no anime"]:
        assert forbidden in out, f"missing forbidden rule: {forbidden}"


def test_apply_brand_style_idempotent():
    prompt = "a hand on a notebook"
    once = visual_style.apply_brand_style(prompt)
    twice = visual_style.apply_brand_style(once)
    assert once == twice, "calling apply_brand_style twice must not double-append"


def test_detect_characters_empty():
    assert characters.detect_characters("a chariot at dawn") == []


def test_detect_arjuna():
    assert characters.detect_characters("Arjuna kneeling on a chariot") == ["Arjuna"]
    assert characters.detect_characters("arjuna stands by his bow") == ["Arjuna"]


def test_detect_krishna():
    assert characters.detect_characters("Krishna speaks beside the chariot") == ["Krishna"]


def test_detect_both():
    out = characters.detect_characters("Arjuna and Krishna on the chariot")
    assert "Arjuna" in out
    assert "Krishna" in out


def test_expand_prompt_adds_arjuna_suffix():
    prompt = "Arjuna kneeling, dawn light, head bowed"
    out = characters.expand_prompt(prompt)
    assert "warrior-prince" in out, "Arjuna canonical suffix must be appended"
    assert "Gandiva" in out
    assert prompt in out


def test_expand_prompt_adds_krishna_suffix():
    prompt = "Krishna seated cross-legged beside the chariot"
    out = characters.expand_prompt(prompt)
    assert "Krishna-blue skin" in out, "Krishna canonical suffix must be appended"
    assert "peacock feather" in out


def test_primary_character_is_earliest_in_prompt():
    # The figure the beat is about (named first) should be the anchor, not the
    # catalog order. "Krishna seated beside Arjuna" is a Krishna beat.
    assert characters.primary_character("Krishna seated beside Arjuna") == "Krishna"
    assert characters.primary_character("Arjuna and Krishna on the chariot") == "Arjuna"


def test_primary_character_none_when_absent():
    assert characters.primary_character("a still pool at dawn, no people") is None


def test_reference_data_uri_for_known_character():
    uri = characters.reference_data_uri("Arjuna")
    assert uri is not None
    assert uri.startswith("data:image/jpeg;base64,")
    # non-trivial payload (the locked reference, not an empty string)
    assert len(uri) > 1000


def test_reference_data_uri_unknown_returns_none():
    assert characters.reference_data_uri("Nobody") is None


def test_expand_prompt_no_characters_unchanged():
    prompt = "a Himalayan dawn, no people"
    assert characters.expand_prompt(prompt) == prompt


def test_expand_prompt_idempotent():
    prompt = "Arjuna standing on a chariot"
    once = characters.expand_prompt(prompt)
    twice = characters.expand_prompt(once)
    assert once == twice


def test_visual_style_then_characters_order():
    """End-to-end: visual-designer writes a prompt mentioning Arjuna.
    Both helpers expand it; the final prompt should contain both the
    brand style and the canonical Arjuna description."""
    prompt = "Arjuna kneeling on a chariot at dawn, head bowed"
    with_chars = characters.expand_prompt(prompt)
    with_style = visual_style.apply_brand_style(with_chars)
    assert "warrior-prince" in with_style
    assert "rich warm cinematic color" in with_style


def test_visual_style_truncates_long_prompts():
    """Regression: MiniMax rejects prompts > ~1400 chars (status 2013).
    The function must keep the total under that limit."""
    long_beat = ("Arjuna standing on a chariot at dawn with bow in hand, "
                 "looking across the battlefield, head bowed, dust settling, "
                 "deep shadows, golden light, contemplative, ancient India, "
                 "warrior, leather wrist guards, handwoven dhoti, "
                 "rust shoulder cloth, no crown, no jewelry") * 3
    out = visual_style.apply_brand_style(long_beat)
    assert len(out) <= 1400, f"expanded prompt is {len(out)} chars, must be <= 1400"
    # Style block must still be present at the tail
    assert "rich warm cinematic color" in out