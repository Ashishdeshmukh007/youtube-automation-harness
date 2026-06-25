import requests
from studio.config import Settings


def _auth(s: Settings) -> dict:
    return {"Authorization": f"Bearer {s.minimax_api_key}", "Content-Type": "application/json"}


def tts_request(s: Settings, text: str, *, speed: float = 0.92, vol: float = 1.0,
                pitch: int = 0):
    url = f"{s.minimax_host}/v1/t2a_v2?GroupId={s.minimax_group_id}"
    payload = {
        "model": s.tts_model,
        "text": text,
        "voice_setting": {"voice_id": s.voice_id, "speed": speed, "vol": vol, "pitch": pitch},
        "audio_setting": {"format": "wav", "sample_rate": 44100, "channel": 1},
    }
    return url, _auth(s), payload


def image_request(s: Settings, prompt: str, *, n: int = 1, aspect_ratio: str = "16:9"):
    url = f"{s.minimax_host}/v1/image_generation"
    payload = {
        "model": s.image_model,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "n": n,
        "response_format": "url",
    }
    return url, _auth(s), payload


def music_request(s: Settings, prompt: str, *, lyrics: str = ""):
    url = f"{s.minimax_host}/v1/music_generation"
    payload = {"model": s.music_model, "prompt": prompt, "lyrics": lyrics}
    return url, _auth(s), payload


def post_json(url: str, headers: dict, payload: dict, *, timeout: int = 120) -> dict:
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
