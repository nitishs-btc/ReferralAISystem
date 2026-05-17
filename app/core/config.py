from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Referral AI System"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    OLLAMA_URL: str = "http://localhost:11434/api/generate"
    OLLAMA_MODEL: str = "llama3.1:8b"
    OLLAMA_TIMEOUT_SECONDS: int = 180
    OLLAMA_CONNECT_TIMEOUT_SECONDS: int = 5
    OLLAMA_MAX_RETRIES: int = 2
    OLLAMA_CONTEXT_WINDOW: int = 8192
    OLLAMA_UNAVAILABLE_COOLDOWN_SECONDS: int = 60

    OCR_TIMEOUT_SECONDS: int = 240
    PIPELINE_TIMEOUT_SECONDS: int = 600
    OCR_CONCURRENCY: int = 2
    LLM_CONCURRENCY: int = 2
    BATCH_CONCURRENCY: int = 4

    MAX_ARCHIVE_FILES: int = 100
    MAX_ARCHIVE_MEMBER_SIZE_MB: int = 50
    SPOOL_CHUNK_SIZE_BYTES: int = 1024 * 1024
    TEMP_DIRECTORY: str = "uploads/tmp"

    REVIEW_CONFIDENCE_THRESHOLD: float = 0.72
    LOW_CONFIDENCE_THRESHOLD: float = 0.60
    CLASSIFIER_DISAGREEMENT_THRESHOLD: float = 0.35
    OCR_POOR_QUALITY_THRESHOLD: float = 0.55
    RULE_REFERRAL_THRESHOLD: float = 0.55
    LLM_REFERRAL_THRESHOLD: float = 0.55
    AGREEMENT_MIN_SCORE: float = 0.65

    OCR_WEIGHT: float = 0.20
    RULE_WEIGHT: float = 0.20
    LLM_WEIGHT: float = 0.25
    EXTRACTION_WEIGHT: float = 0.20
    VALIDATION_WEIGHT: float = 0.15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def temp_directory_path(self) -> Path:
        return Path(self.TEMP_DIRECTORY)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
