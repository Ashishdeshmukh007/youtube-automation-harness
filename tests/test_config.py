from studio.config import load_settings


def test_load_settings_reads_env(monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-test")
    monkeypatch.setenv("MINIMAX_HOST", "https://api.minimax.io")
    monkeypatch.setenv("MINIMAX_VOICE_ID", "stoic_male")
    s = load_settings()
    assert s.minimax_api_key == "sk-test"
    assert s.minimax_host == "https://api.minimax.io"
    assert s.voice_id == "stoic_male"
    assert s.tts_model == "speech-2.8-hd"  # default applied


def test_load_settings_missing_key_raises(monkeypatch):
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    import pytest
    with pytest.raises(ValueError, match="MINIMAX_API_KEY"):
        load_settings()
