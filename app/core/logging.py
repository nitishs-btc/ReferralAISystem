"""Logging bootstrap for the backend's structured, stage-aware application logs."""

import logging
from logging.config import dictConfig


def configure_logging(level: str = "INFO") -> None:
    # Use a single consistent formatter so OCR, LLM, and pipeline events are easy to trace.
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": (
                        "%(asctime)s %(levelname)s %(name)s "
                        "event=%(message)s %(stage)s %(document_id)s %(details)s"
                    )
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": level,
                }
            },
            "loggers": {
                "referral_ai": {
                    "handlers": ["default"],
                    "level": level,
                    "propagate": False,
                }
            },
        }
    )

    logging.getLogger("referral_ai").debug(
        "logging_configured",
        extra={"stage": "-", "document_id": "-", "details": "{}"},
    )
