from studio import pronunciation


def test_respells_known_sanskrit_terms():
    out = pronunciation.apply("He spoke of dharma to Arjuna.")
    assert "dharma" not in out.lower().split()  # the raw token is gone
    assert "Arjuna" not in out


def test_case_insensitive_and_preserves_leading_capital():
    # mid-sentence capitalized name stays capitalized after respelling
    out = pronunciation.apply("Then Gita and the gita again")
    # both occurrences respelled; the capitalized one keeps a leading capital
    assert "Gita" not in out
    assert out.split()[1][0].isupper()


def test_word_boundary_only():
    # must not rewrite a Sanskrit term embedded in an unrelated word
    out = pronunciation.apply("digital dharmas")  # 'gita' inside 'digital'
    assert "digital" in out


def test_plain_text_unchanged():
    text = "You are not behind. You are on your road."
    assert pronunciation.apply(text) == text
