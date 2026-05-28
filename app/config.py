from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    ENV: str = "development"
    SECRET_KEY: str = "9aefc882875b4dbab2059346d03cf955848e02d64f0616b2bc3193ce140c883e"
    
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

settings = Settings()
