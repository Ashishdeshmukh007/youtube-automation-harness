import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    minimax_api_key: str
    minimax_host: str
    minimax_group_id: str
    voice_id: str
    tts_model: str
    image_model: str
    music_model: str
    youtube_client_secret: str
    youtube_token: str


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise ValueError(f"Missing required env var: {name}")
    return val


def load_settings() -> Settings:
    return Settings(
        minimax_api_key=_require("MINIMAX_API_KEY"),
        minimax_host=os.getenv("MINIMAX_HOST", "https://api.minimax.io"),
        minimax_group_id=os.getenv("MINIMAX_GROUP_ID", ""),
        voice_id=os.getenv("MINIMAX_VOICE_ID", ""),
        tts_model=os.getenv("MINIMAX_TTS_MODEL", "speech-2.8-hd"),
        image_model=os.getenv("MINIMAX_IMAGE_MODEL", "image-01"),
        music_model=os.getenv("MINIMAX_MUSIC_MODEL", "music-2.6"),
        youtube_client_secret=os.getenv("YOUTUBE_CLIENT_SECRET", "client_secret.json"),
        youtube_token=os.getenv("YOUTUBE_TOKEN", "youtube_token.json"),
    )
