from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/reachout"

    # Auth
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "changeme123"

    # People search providers
    PDL_API_KEY: Optional[str] = None
    APOLLO_API_KEY: Optional[str] = None
    PROXYCURL_API_KEY: Optional[str] = None
    CORESIGNAL_API_KEY: Optional[str] = None

    # Voice calling provider
    HUNAR_API_KEY: Optional[str] = None
    HUNAR_BASE_URL: str = "https://api.voice.hunar.ai/external/v1"

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:5173"


settings = Settings()
