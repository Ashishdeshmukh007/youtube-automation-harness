from pathlib import Path
from studio.config import Settings
from studio.providers import minimax
from studio.types import MediaResult
from studio import pronunciation


def synthesize(s: Settings, text: str, out_path: Path, *,
               speed: float = 0.85, emotion: str = "neutral") -> MediaResult:
    """Synthesize narration via MiniMax speech-2.8-hd.

    Defaults: speed=0.85 (slower than naive default for steadier prosody on
    long monologues — speech-2.8-hd tends to drift in pitch/emotion at higher
    speeds, and we want a calm, grounded delivery).
    emotion="neutral" pins the model to neutral affect, reducing the
    variation between sentences.
    """
    # Respell Sanskrit terms phonetically so the English-trained voice pronounces
    # them clearly (dharma, Arjuna, Gita, Upanishads, ...).
    spoken = pronunciation.apply(text)
    url, headers, payload = minimax.tts_request(
        s, spoken, speed=speed, emotion=emotion)
    data = minimax.post_json(url, headers, payload)
    audio_hex = data["data"]["audio"]
    out_path.write_bytes(bytes.fromhex(audio_hex))
    return MediaResult(
        path=out_path,
        usage={"characters": len(text), "speed": speed, "emotion": emotion},
    )
