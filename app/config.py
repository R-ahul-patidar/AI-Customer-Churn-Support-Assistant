"""
Application configuration using pydantic-settings.
All settings are read from environment variables or .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./churn_assistant.db"

    # Gemini AI (Phase 3)
    gemini_api_key: str = ""


# Singleton settings instance
settings = Settings()
