"""Settings read from backend/.env (never committed)."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

HERE = Path(__file__).parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=HERE / ".env", extra="ignore")
    zernio_api_key: str = ""
    zernio_base_url: str = "https://zernio.com/api/v1"
    default_timezone: str = "Asia/Dubai"
    max_video_mb: int = 300
    ollama_url: str = "http://localhost:11434"
    vision_model: str = "qwen2.5vl:7b"   # looks at video frames
    text_model: str = "qwen2.5:7b-instruct"  # writes titles, captions, hashtags
    analyze_frames: int = 6
    database_url: str = f"sqlite+aiosqlite:///{HERE / 'poc.db'}"


settings = Settings()
