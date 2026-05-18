"""Small logging helper that standardizes stage/document context across backend services."""

import logging
from contextlib import contextmanager
from time import perf_counter


class LoggingService:
    def __init__(self) -> None:
        self.logger = logging.getLogger("referral_ai")

    def info(self, event: str, *, stage: str = "-", document_id: str = "-", **details) -> None:
        self.logger.info(
            event,
            extra={
                "stage": stage,
                "document_id": document_id,
                "details": details or {},
            },
        )

    def warning(self, event: str, *, stage: str = "-", document_id: str = "-", **details) -> None:
        self.logger.warning(
            event,
            extra={
                "stage": stage,
                "document_id": document_id,
                "details": details or {},
            },
        )

    def error(self, event: str, *, stage: str = "-", document_id: str = "-", **details) -> None:
        self.logger.error(
            event,
            extra={
                "stage": stage,
                "document_id": document_id,
                "details": details or {},
            },
        )

    @contextmanager
    def timed(self, event: str, *, stage: str, document_id: str):
        # Useful for ad hoc timing when a service wants start/end events without repeating boilerplate.
        start = perf_counter()
        self.info(f"{event}_started", stage=stage, document_id=document_id)
        try:
            yield
        finally:
            duration_ms = round((perf_counter() - start) * 1000, 2)
            self.info(
                f"{event}_completed",
                stage=stage,
                document_id=document_id,
                duration_ms=duration_ms,
            )
