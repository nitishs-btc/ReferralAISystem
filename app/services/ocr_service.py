import asyncio
from pathlib import Path

from docling.document_converter import DocumentConverter

from app.core.config import settings
from app.core.exceptions import OCRProcessingError
from app.schemas.referral import OCRQualityMetrics, OCRResult
from app.services.file_handler_service import NormalizedDocument
from app.services.logging_service import LoggingService


class OCRService:
    def __init__(self) -> None:
        self.converter = DocumentConverter()
        self.logger = LoggingService()
        self.semaphore = asyncio.Semaphore(settings.OCR_CONCURRENCY)

    async def extract(self, document: NormalizedDocument) -> OCRResult:
        async with self.semaphore:
            try:
                payload = await asyncio.wait_for(
                    asyncio.to_thread(self._extract_sync, document.file_path),
                    timeout=settings.OCR_TIMEOUT_SECONDS,
                )
                return payload
            except TimeoutError as exc:
                raise OCRProcessingError("OCR timed out") from exc
            except Exception as exc:  # pragma: no cover - defensive production guard
                raise OCRProcessingError(str(exc)) from exc

    def _extract_sync(self, file_path: Path) -> OCRResult:
        result = self.converter.convert(str(file_path))
        document = result.document

        raw_text = document.export_to_text() or ""
        markdown = document.export_to_markdown() or ""
        total_pages = len(document.pages or [])

        text_density = min(len(raw_text.strip()) / max(total_pages, 1) / 1500.0, 1.0) if raw_text else 0.0
        blank_document = not raw_text.strip()
        average_confidence = 0.15 if blank_document else min(0.55 + (text_density * 0.45), 0.98)
        blank_page_ratio = 1.0 if blank_document else 0.0
        poor_quality = average_confidence < settings.OCR_POOR_QUALITY_THRESHOLD

        return OCRResult(
            raw_text=raw_text,
            markdown=markdown,
            total_pages=total_pages,
            average_confidence=round(average_confidence, 4),
            blank_document=blank_document,
            corrupted_document=False,
            quality=OCRQualityMetrics(
                average_confidence=round(average_confidence, 4),
                text_density=round(text_density, 4),
                blank_page_ratio=round(blank_page_ratio, 4),
                poor_quality=poor_quality,
            ),
        )
