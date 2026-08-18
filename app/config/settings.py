from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # General
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    # Agent defaults
    DEFAULT_TIMEOUT_SECONDS: int = 120
    DEFAULT_RETRY_LIMIT: int = 3
    DEFAULT_MODEL: str = "gpt-4"

    # AI Services (placeholder)
    AI_SERVICES_URL: Optional[str] = None
    AI_SERVICES_API_KEY: Optional[str] = None

    # Tools
    SEARCH_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()