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
    meta_access_token: str = ""   # Graph API user token (short-lived ones last about 1 hour)
    meta_graph_version: str = "v21.0"
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_redirect_uri: str = "http://localhost:8100/api/youtube/callback"  # must match the Google console exactly
    frontend_url: str = "http://localhost:3100"
    threads_access_token: str = ""  # Threads has its own token (threads_basic, threads_content_publish)
    ollama_url: str = "http://localhost:11434"
    vision_model: str = "qwen2.5vl:7b"   # looks at video frames
    num_ctx: int = 16384   # context window; Ollama defaults to 4096, too small for several video frames
    text_model: str = "qwen2.5:7b-instruct"  # writes titles, captions, hashtags
    analyze_frames: int = 6
    database_url: str = f"sqlite+aiosqlite:///{HERE / 'poc.db'}"


settings = Settings()
