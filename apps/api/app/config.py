from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://promptforge:promptforge@localhost:5432/promptforge"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-use-at-least-32-chars!!"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    groq_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"


settings = Settings()
