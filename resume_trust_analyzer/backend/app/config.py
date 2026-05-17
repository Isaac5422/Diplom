from functools import lru_cache
from pydantic import BaseModel, Field
import os


def _default_cors_origins() -> list[str]:
    return [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]


class Settings(BaseModel):
    app_name: str = "Resume Trust Analyzer"
    app_env: str = os.getenv("APP_ENV", "local")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./resume_trust.sqlite3")
    cors_origins: list[str] = Field(default_factory=_default_cors_origins)
    github_token: str | None = os.getenv("GITHUB_TOKEN")
    hh_token: str | None = os.getenv("HH_TOKEN")


@lru_cache
def get_settings() -> Settings:
    return Settings()
