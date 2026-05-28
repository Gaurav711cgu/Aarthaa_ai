from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    ENV: str = "development"
    SECRET_KEY: str = "placeholder_secret_key_minimum_32_characters"
    
    POSTGRES_USER: str = "artha_admin"
    POSTGRES_PASSWORD: str = "artha_password_secure_2026"
    POSTGRES_DB: str = "artha_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
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
        if self.SECRET_KEY:
            assert len(self.SECRET_KEY) >= 32, "SECRET_KEY too short"
        if self.ENV == "production":
            if not self.SECRET_KEY or self.SECRET_KEY == "placeholder_secret_key_minimum_32_characters":
                raise ValueError("SECRET_KEY must be set in production mode!")
            if not self.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY must be set in production mode!")

settings = Settings()

