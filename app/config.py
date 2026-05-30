from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Sentinel — detected at startup to enforce no-default-secret policy in ALL environments
_PLACEHOLDER_SECRET = "artha_dev_placeholder_secret_key_32chars"

class Settings(BaseSettings):
    ENV: str = "development"
    # No hardcoded production secret — provide via environment variable or .env file
    SECRET_KEY: str = _PLACEHOLDER_SECRET

    POSTGRES_USER: str = "artha_admin"
    POSTGRES_PASSWORD: str = "artha_password_secure_2026"
    POSTGRES_DB: str = "artha_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin_password_2026"
    ANALYST_USERNAME: str = "analyst"
    ANALYST_PASSWORD: str = "analyst_password_2026"
    READONLY_USERNAME: str = "readonly"
    READONLY_PASSWORD: str = "readonly_password_2026"

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def __init__(self, **values):
        super().__init__(**values)

        # Enforce minimum key length in every environment
        if not self.SECRET_KEY or len(self.SECRET_KEY) < 32:
            raise ValueError(
                "STARTUP FAILURE: SECRET_KEY must be at least 32 characters. "
                "Set it via the SECRET_KEY environment variable or .env file."
            )

        # Warn loudly if the placeholder is still in use (dev only — never commit real keys)
        if self.SECRET_KEY == _PLACEHOLDER_SECRET:
            import logging
            logging.getLogger(__name__).warning(
                "⚠️  SECRET_KEY is using the default placeholder. "
                "Set a real SECRET_KEY environment variable before any production or demo deployment."
            )

        # Hard-fail in production if placeholder or missing Groq key
        if self.ENV == "production":
            if self.SECRET_KEY == _PLACEHOLDER_SECRET:
                raise ValueError(
                    "STARTUP FAILURE: Placeholder SECRET_KEY is not allowed in production. "
                    "Set a cryptographically secure SECRET_KEY in your environment."
                )
            if not self.GROQ_API_KEY:
                raise ValueError(
                    "STARTUP FAILURE: GROQ_API_KEY must be set in production mode."
                )

settings = Settings()

