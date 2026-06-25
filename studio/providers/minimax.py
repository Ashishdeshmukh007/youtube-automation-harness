import requests
from studio.config import Settings


def _auth(s: Settings) -> dict:
    return {"Authorization": f"Bearer {s.minimax_api_key}", "Content-Type": "application/json"}


def tts_request(s: Settings, text: str, *, speed: float = 0.85, vol: float = 1.0,
                pitch: int = 0, emotion: str = "neutral"):
    url = f"{s.minimax_host}/v1/t2a_v2?GroupId={s.minimax_group_id}"
    payload = {
        "model": s.tts_model,
        "text": text,
        "voice_setting": {
            "voice_id": s.voice_id, "speed": speed, "vol": vol, "pitch": pitch,
        },
        "audio_setting": {"format": "wav", "sample_rate": 44100, "channel": 1},
    }
    # Emotion is optional in the MiniMax payload; only include if explicitly set
    # to a non-default value (helps avoid accidental invalid-param errors).
    if emotion and emotion != "neutral":
        payload["voice_setting"]["emotion"] = emotion
    return url, _auth(s), payload


def image_request(s: Settings, prompt: str, *, n: int = 1, aspect_ratio: str = "16:9",
                  subject_reference: list | None = None):
    url = f"{s.minimax_host}/v1/image_generation"
    payload = {
        "model": s.image_model,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "n": n,
        "response_format": "url",
    }
    # subject_reference (image-01) conditions generation on a character portrait,
    # so a recurring figure keeps the same face/clothing across shots and episodes.
    if subject_reference:
        payload["subject_reference"] = subject_reference
    return url, _auth(s), payload


def music_request(s: Settings, prompt: str, *, lyrics: str = " "):
    url = f"{s.minimax_host}/v1/music_generation"
    payload = {"model": s.music_model, "prompt": prompt, "lyrics": lyrics}
    return url, _auth(s), payload


# Music generation can take ~2 minutes for an ambient track; the default 120s
# timeout in post_json is too tight. Music callers use this longer window.
_MUSIC_TIMEOUT = 240


def post_json(url: str, headers: dict, payload: dict, *, timeout: int = 120) -> dict:
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def post_music(url: str, headers: dict, payload: dict) -> dict:
    """Post a music_generation request with the longer timeout."""
    return post_json(url, headers, payload, timeout=_MUSIC_TIMEOUT)
