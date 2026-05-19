"""Batch-safe orchestration that isolates errors per file and preserves API compatibility."""

import asyncio

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ArchiveExtractionError, UnsupportedFileTypeError
from app.schemas.referral import BatchFileResult, BatchProcessingResult, BatchSummary, DocumentAnalysisResult
from app.services.file_handler_service import FileHandlerService
from app.services.logging_service import LoggingService


class BatchOrchestrator:
    def __init__(self, pipeline: "ReferralPipeline", file_handler: FileHandlerService) -> None:
        self.pipeline = pipeline
        self.file_handler = file_handler
        self.logger = LoggingService()
        self.semaphore = asyncio.Semaphore(settings.BATCH_CONCURRENCY)

    async def process_uploads(self, files: list[UploadFile]) -> BatchProcessingResult:
        tasks = [self._process_upload(file) for file in files]
        nested_results = await asyncio.gather(*tasks)
        results = [item for file_results in nested_results for item in file_results]
        return self._summarize(results)

    async def process_archive(self, upload: UploadFile) -> BatchProcessingResult:
        return self._summarize(await self._process_upload(upload))

    async def _process_upload(self, upload: UploadFile) -> list[BatchFileResult]:
        try:
            documents = await self.file_handler.normalize_upload(upload)
        except (UnsupportedFileTypeError, ArchiveExtractionError) as exc:
            return [BatchFileResult(filename=upload.filename or "unknown", status="error", error=str(exc))]

        try:
            # Process normalized documents independently so one archive member cannot block the rest.
            tasks = [self._process_document(document) for document in documents]
            return await asyncio.gather(*tasks)
        finally:
            await self.file_handler.cleanup_documents(documents)

    async def _process_document(self, document) -> BatchFileResult:
        async with self.semaphore:
            try:
                result = await self.pipeline.process_document(document)
                return BatchFileResult(
                    filename=document.filename,
                    status="success",
                    data=self.pipeline.to_api_data(result),
                    analysis=result.model_dump(),
                )
            except Exception as exc:  # pragma: no cover - safety net for batch isolation
                self.logger.error(
                    "document_processing_failed",
                    stage="batch",
                    document_id=document.document_id,
                    error=str(exc),
                )
                return BatchFileResult(filename=document.filename, status="error", error=str(exc))

    def _summarize(self, results: list[BatchFileResult]) -> BatchProcessingResult:
        # Summary stats drive the dashboard overview and basic operational reporting.
        successful = sum(1 for item in results if item.status == "success")
        failed = len(results) - successful
        human_review_required = sum(
        1 for item in results
        if item.data and _get_needs_review(item.data.review)
    )
        return BatchProcessingResult(
            summary=BatchSummary(
                total_files=len(results),
                successful=successful,
                failed=failed,
                human_review_required=human_review_required,
            ),
            results=results,
        )

def _get_needs_review(review) -> bool:
    """Safely read needs_human_review from either a Pydantic model or a plain dict."""
    if review is None:
        return False
    if isinstance(review, dict):
        return review.get("needs_human_review", False)
    return getattr(review, "needs_human_review", False)