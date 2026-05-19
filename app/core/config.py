"""Central application settings loaded from environment variables and cached once per process."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    # App/runtime settings.
    APP_NAME: str
    APP_ENV: str
    LOG_LEVEL: str
    CORS_ORIGINS: Annotated[list[str], NoDecode]

    # LLM connectivity and retry controls.
    OLLAMA_URL: str
    OLLAMA_MODEL: str
    OLLAMA_TIMEOUT_SECONDS: int
    OLLAMA_CONNECT_TIMEOUT_SECONDS: int
    OLLAMA_MAX_RETRIES: int
    OLLAMA_CONTEXT_WINDOW: int
    OLLAMA_UNAVAILABLE_COOLDOWN_SECONDS: int

    # Workload throttling to protect CPU/RAM during batch processing.
    OCR_TIMEOUT_SECONDS: int
    PIPELINE_TIMEOUT_SECONDS: int
    OCR_CONCURRENCY: int
    LLM_CONCURRENCY: int
    BATCH_CONCURRENCY: int

    # File handling safeguards for large uploads and archives.
    MAX_ARCHIVE_FILES: int
    MAX_ARCHIVE_MEMBER_SIZE_MB: int
    SPOOL_CHUNK_SIZE_BYTES: int
    TEMP_DIRECTORY: str

    # Decision thresholds used by classification, validation, and review routing.
    REVIEW_CONFIDENCE_THRESHOLD: float
    LOW_CONFIDENCE_THRESHOLD: float
    CLASSIFIER_DISAGREEMENT_THRESHOLD: float
    OCR_POOR_QUALITY_THRESHOLD: float
    RULE_REFERRAL_THRESHOLD: float
    MIN_TEXT_ALPHA_CHARS_FOR_LLM: int
    USE_RULE_GATE_FOR_LLM: bool
    RULE_LLM_GATE_THRESHOLD: float
    LLM_REFERRAL_THRESHOLD: float
    AGREEMENT_MIN_SCORE: float
    CONSIDER_FOR_HUMAN_REVIEW: float

    # Weighted confidence fusion inputs.
    OCR_WEIGHT: float
    RULE_WEIGHT: float
    LLM_WEIGHT: float
    EXTRACTION_WEIGHT: float
    VALIDATION_WEIGHT: float

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        # Allow .env to provide CORS origins as a comma-separated string.
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def temp_directory_path(self) -> Path:
        # Resolve lazily so callers always get a Path object instead of a raw string.
        return Path(self.TEMP_DIRECTORY)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Cache settings so repeated imports do not reload the environment or rebuild the model.
    return Settings()


settings = get_settings()
