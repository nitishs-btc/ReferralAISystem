"""OCR adapter that runs Docling behind async-friendly semaphores and timeouts."""

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
                # OCR is blocking and CPU-heavy, so it is pushed onto a worker thread.
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

        # Docling does not expose a single native confidence here, so we derive a quality heuristic from
        # text density and blank output to support downstream review routing.
        text_density = min(len(raw_text.strip()) / max(total_pages, 1) / 1500.0, 1.0) if raw_text else 0.0
        blank_document = not raw_text.strip()
        average_confidence = 0.15 if blank_document else min(0.55 + (text_density * 0.45), 0.98)
        blank_page_ratio = 1.0 if blank_document else 0.0
        poor_quality = average_confidence < settings.OCR_POOR_QUALITY_THRESHOLD

        self._save_ocr_output(file_path, raw_text, markdown)

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

    def _save_ocr_output(self, file_path: Path, raw_text: str, markdown: str) -> None:
        try:
            output_dir = Path(settings.OCR_OUTPUT_DIRECTORY) / file_path.stem
            output_dir.mkdir(parents=True, exist_ok=True)

            (output_dir / "raw_text.txt").write_text(raw_text, encoding="utf-8")
            (output_dir / "markdown.md").write_text(markdown, encoding="utf-8")

            self.logger.info(
                "ocr_output_saved",
                stage="ocr",
                path=str(output_dir),
            )
        except Exception as exc:
            # Never let a save failure break the pipeline — log and continue
            self.logger.warning(
                "ocr_output_save_failed",
                stage="ocr",
                error=str(exc),
            )
