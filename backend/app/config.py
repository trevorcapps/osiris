from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"

    # API Keys (all optional — feeds degrade gracefully)
    cesium_ion_token: Optional[str] = None
    opensky_username: Optional[str] = None
    opensky_password: Optional[str] = None
    aisstream_api_key: Optional[str] = None
    shodan_api_key: Optional[str] = None
    greynoise_api_key: Optional[str] = None
    otx_api_key: Optional[str] = None
    acled_username: Optional[str] = None  # myACLED email
    acled_password: Optional[str] = None  # myACLED password
    nasa_firms_api_key: Optional[str] = None

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
