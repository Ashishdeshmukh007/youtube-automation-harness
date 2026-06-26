"""fal.ai provider — image-to-video (Wan 2.2) for the hybrid pipeline.

fal uses an async queue API: submit -> poll status -> fetch result. The studio
calls these to animate a still into a short cinematic clip.
"""
import time
import requests

I2V_MODEL = "fal-ai/wan/v2.2-a14b/image-to-video"


def _auth(fal_key: str) -> dict:
    return {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}


def i2v_request(fal_key: str, image_url: str, prompt: str, *, model: str = I2V_MODEL,
                resolution: str = "480p"):
    """Build (url, headers, payload) for an image-to-video submission.
    image_url may be a public URL or a base64 data URI. resolution "480p" (default,
    cheaper — upscaled to 1080p in assembly) or "720p"."""
    url = f"https://queue.fal.run/{model}"
    # Disable the input safety checker — it false-positives on our devotional /
    # battlefield art (bare-chested deities, etc.), blocking otherwise fine frames.
    payload = {"image_url": image_url, "prompt": prompt,
               "resolution": resolution, "enable_safety_checker": False}
    return url, _auth(fal_key), payload


def result_video_url(result: dict) -> str | None:
    """Pull the clip URL out of a completed result payload."""
    return (result.get("video") or {}).get("url")


def submit(url: str, headers: dict, payload: dict, *, timeout: int = 60) -> dict:
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def get_result(response_url: str, headers: dict, *, timeout: int = 60) -> dict:
    resp = requests.get(response_url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def poll_until_done(status_url: str, headers: dict, *, interval: int = 10,
                    max_wait: int = 900) -> dict:
    """Poll a fal status_url until COMPLETED (or raise on failure/timeout)."""
    waited = 0
    while waited < max_wait:
        time.sleep(interval)
        waited += interval
        st = requests.get(status_url, headers=headers, timeout=60).json()
        status = st.get("status")
        if status == "COMPLETED":
            return st
        if status in ("FAILED", "ERROR"):
            raise RuntimeError(f"fal job failed: {st}")
    raise TimeoutError(f"fal job not done after {max_wait}s")
