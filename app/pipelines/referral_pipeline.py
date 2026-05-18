"""Primary workflow orchestrator for intake, OCR, classification, extraction, and review."""

from time import perf_counter

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import OCRProcessingError
from app.schemas.referral import (
    ApiReferralData,
    ClassificationResult,
    DocumentAnalysisResult,
    DocumentCategory,
    DocumentState,
    ExtractedReferralData,
    FileMetadata,
    OCRResult,
    ProcessingTimings,
    ReferralType,
    ValidationInformation,
)
from app.services.batch_orchestrator import BatchOrchestrator
from app.services.classification_service import ClassificationService
from app.services.confidence_fusion_service import ConfidenceFusionService
from app.services.extraction_service import ExtractionService
from app.services.file_handler_service import FileHandlerService, NormalizedDocument
from app.services.llm_service import LLMService
from app.services.logging_service import LoggingService
from app.services.ocr_service import OCRService
from app.services.review_routing_service import ReviewRoutingService
from app.services.validation_service import ValidationService


class ReferralPipeline:
    _instance: "ReferralPipeline | None" = None

    def __init__(self) -> None:
        # Build service dependencies once so semaphores, prompt caches, and clients are reused.
        self.logger = LoggingService()
        self.file_handler = FileHandlerService()
        self.llm_service = LLMService()
        self.ocr_service = OCRService()
        self.classification_service = ClassificationService(self.llm_service)
        self.extraction_service = ExtractionService(self.llm_service)
        self.validation_service = ValidationService()
        self.confidence_fusion_service = ConfidenceFusionService()
        self.review_routing_service = ReviewRoutingService()
        self.batch_orchestrator = BatchOrchestrator(self, self.file_handler)

    @classmethod
    def instance(cls) -> "ReferralPipeline":
        # The pipeline is effectively stateless per request, so a singleton keeps setup overhead low.
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    async def process(file: UploadFile):
        pipeline = ReferralPipeline.instance()
        documents = await pipeline.file_handler.normalize_upload(file)
        try:
            if len(documents) != 1:
                raise ValueError("Single document endpoint received an archive or multiple logical documents.")
            # The single-file endpoint returns only the dashboard-compatible data payload.
            result = await pipeline.process_document(documents[0])
            return pipeline.to_api_data(result).model_dump()
        finally:
            await pipeline.file_handler.cleanup_documents(documents)

    @staticmethod
    async def process_batch(files: list[UploadFile]):
        pipeline = ReferralPipeline.instance()
        return pipeline.batch_orchestrator.process_uploads(files)

    @staticmethod
    async def process_archive(file: UploadFile):
        pipeline = ReferralPipeline.instance()
        return pipeline.batch_orchestrator.process_archive(file)

    async def process_document(self, document: NormalizedDocument) -> DocumentAnalysisResult:
        # Track stage timings so slow OCR/LLM steps are visible in logs and API metadata.
        start_total = perf_counter()
        timings = ProcessingTimings()
        self.logger.info("document_processing_started", stage="pipeline", document_id=document.document_id, filename=document.filename)

        file_metadata = FileMetadata(
            filename=document.filename,
            source_filename=document.source_filename,
            content_type=document.content_type,
            file_extension=document.file_extension,
            file_size_bytes=document.file_size_bytes,
            is_archive_member=document.is_archive_member,
        )

        ocr_start = perf_counter()
        try:
            ocr = await self.ocr_service.extract(document)
        except OCRProcessingError as exc:
            # OCR failure should degrade this document only; the batch must continue.
            ocr = OCRResult(corrupted_document=True, total_pages=0, raw_text="", markdown="")
            classification = ClassificationResult(
                document_state=DocumentState.CORRUPTED_DOCUMENT,
                document_type="Corrupted Document",
                document_category=DocumentCategory.UNKNOWN,
                referral_type=ReferralType.UNKNOWN,
                is_referral_candidate=False,
                confidence=0.0,
            )
            validation = ValidationInformation(
                is_complete_referral=False,
                missing_fields=[],
                warnings=["OCR processing failed."],
                needs_human_review=True,
                validation_confidence=0.0,
                applied_rule_profile="corrupted_document",
            )
            extracted = ExtractedReferralData(
                is_referral_document=False,
                document_type="Corrupted Document",
                document_category=DocumentCategory.UNKNOWN.value,
                referral_type=ReferralType.UNKNOWN.value,
                validation=validation,
            )
            confidence = self.confidence_fusion_service.fuse(
                classification=classification,
                extracted_data=extracted,
                validation=validation,
                ocr=ocr,
            )
            review = self.review_routing_service.route(
                classification=classification,
                confidence=confidence,
                validation=validation,
                ocr=ocr,
            )
            timings.ocr_ms = round((perf_counter() - ocr_start) * 1000, 2)
            timings.total_ms = round((perf_counter() - start_total) * 1000, 2)
            return DocumentAnalysisResult(
                document_id=document.document_id,
                status="error",
                file=file_metadata,
                total_pages=0,
                document_state=DocumentState.CORRUPTED_DOCUMENT,
                document_type="Corrupted Document",
                document_category=DocumentCategory.UNKNOWN.value,
                referral_type=ReferralType.UNKNOWN.value,
                ocr=ocr,
                classification=classification,
                extracted_data=extracted,
                validation=validation,
                confidence=confidence,
                review=review,
                timings=timings,
                errors=[str(exc)],
                audit={"pipeline_version": "2.0", "degraded_mode": True},
            )
        timings.ocr_ms = round((perf_counter() - ocr_start) * 1000, 2)

        classification_start = perf_counter()
        classification = await self.classification_service.classify(document_id=document.document_id, ocr=ocr)
        timings.classification_ms = round((perf_counter() - classification_start) * 1000, 2)

        extraction_start = perf_counter()
        if classification.is_referral_candidate:
            # We only spend extraction cost on likely referral candidates.
            extracted = await self.extraction_service.extract(
                document_id=document.document_id,
                classification=classification,
                ocr=ocr,
            )
        else:
            extracted = ExtractedReferralData(
                is_referral_document=False,
                document_type=classification.document_type,
                document_category=classification.document_category.value,
                referral_type=classification.referral_type.value,
            )
        timings.extraction_ms = round((perf_counter() - extraction_start) * 1000, 2)

        validation_start = perf_counter()
        validation = self.validation_service.validate(
            classification=classification,
            extracted_data=extracted,
            ocr=ocr,
        )
        extracted.validation = validation
        timings.validation_ms = round((perf_counter() - validation_start) * 1000, 2)

        fusion_start = perf_counter()
        confidence = self.confidence_fusion_service.fuse(
            classification=classification,
            extracted_data=extracted,
            validation=validation,
            ocr=ocr,
        )
        timings.fusion_ms = round((perf_counter() - fusion_start) * 1000, 2)

        document_state = self._resolve_final_state(classification, extracted, validation, confidence, ocr)
        classification.document_state = document_state
        # Keep the extracted document label aligned with the final state shown in the UI.
        if document_state == DocumentState.INCOMPLETE_REFERRAL:
            extracted.document_type = "Incomplete Referral"
        elif document_state == DocumentState.SELF_REFERRAL:
            extracted.document_type = "Self Referral Form"

        review_start = perf_counter()
        review = self.review_routing_service.route(
            classification=classification,
            confidence=confidence,
            validation=validation,
            ocr=ocr,
        )
        timings.review_ms = round((perf_counter() - review_start) * 1000, 2)
        timings.total_ms = round((perf_counter() - start_total) * 1000, 2)

        self.logger.info(
            "document_processing_completed",
            stage="pipeline",
            document_id=document.document_id,
            document_state=document_state.value,
            total_ms=timings.total_ms,
        )

        return DocumentAnalysisResult(
            document_id=document.document_id,
            status="success",
            file=file_metadata,
            total_pages=ocr.total_pages,
            document_state=document_state,
            document_type=extracted.document_type or classification.document_type,
            document_category=classification.document_category.value,
            referral_type=classification.referral_type.value,
            ocr=ocr,
            classification=classification,
            extracted_data=extracted,
            validation=validation,
            confidence=confidence,
            review=review,
            timings=timings,
            errors=[],
            audit={
                "pipeline_version": "2.0",
                "llm_available": classification.llm_available,
                "needs_human_review": review.needs_human_review,
            },
        )

    def to_api_data(self, result: DocumentAnalysisResult) -> ApiReferralData:
        # Preserve the original frontend contract while exposing richer metadata for future UI work.
        extracted = result.extracted_data
        is_referral_document = result.document_state in {
            DocumentState.VALID_REFERRAL,
            DocumentState.INCOMPLETE_REFERRAL,
            DocumentState.SELF_REFERRAL,
            DocumentState.LOW_CONFIDENCE_REFERRAL,
        }
        confidence_scores = {
            key: self._to_percent(value) for key, value in extracted.confidence_scores.items()
        }
        confidence_scores.update(
            {
                "overall": self._to_percent(result.confidence.final_confidence_score),
                "ocr": self._to_percent(result.ocr.average_confidence),
                "rule": self._to_percent(result.classification.evidence.rule_score),
                "llm": self._to_percent(result.classification.evidence.llm_score),
                "classification": self._to_percent(result.classification.confidence),
                "validation": self._to_percent(result.validation.validation_confidence),
                "classifier_agreement": self._to_percent(result.classification.evidence.agreement_score),
                "completeness": self._to_percent(result.validation.completeness_score),
            }
        )

        return ApiReferralData(
            is_referral_document=is_referral_document,
            document_type=result.document_type,
            document_state=result.document_state.value,
            document_category=result.document_category,
            referral_type=result.referral_type,
            patient_information=extracted.patient_information,
            provider_information=extracted.provider_information,
            insurance_information=extracted.insurance_information,
            clinical_information=extracted.clinical_information,
            validation=result.validation,
            confidence_scores=confidence_scores,
            classification={
                "document_state": result.document_state.value,
                "document_type": result.document_type,
                "document_category": result.document_category,
                "referral_type": result.referral_type,
                "rule_score": self._to_percent(result.classification.evidence.rule_score),
                "llm_score": self._to_percent(result.classification.evidence.llm_score),
                "final_classification_score": self._to_percent(result.classification.confidence),
                "passed_rule_threshold": result.classification.evidence.passed_rule_threshold,
                "passed_llm_threshold": result.classification.evidence.passed_llm_threshold,
                "classifier_agreement": self._to_percent(result.classification.evidence.agreement_score),
                "agreement_within_threshold": result.classification.evidence.agreement_within_threshold,
                "reason": result.classification.evidence.explanation,
                "positive_signals": result.classification.evidence.positive_signals,
                "negative_signals": result.classification.evidence.negative_signals,
            },
            ocr={
                "total_pages": result.total_pages,
                "average_confidence": self._to_percent(result.ocr.average_confidence),
                "poor_quality": result.ocr.quality.poor_quality,
                "blank_document": result.ocr.blank_document,
            },
            review={
                "needs_human_review": result.review.needs_human_review,
                "priority": result.review.priority.value,
                "queue": result.review.queue,
                "reasons": result.review.reasons,
            },
            metadata={
                "file": result.file.model_dump(),
                "timings": result.timings.model_dump(),
            },
        )

    def _resolve_final_state(
        self,
        classification: ClassificationResult,
        extracted: ExtractedReferralData,
        validation: ValidationInformation,
        confidence,
        ocr: OCRResult,
    ) -> DocumentState:
        # Final state is intentionally stricter than early classification because it includes extraction
        # quality, validation completeness, OCR quality, and rule/LLM agreement.
        if ocr.blank_document:
            return DocumentState.BLANK_DOCUMENT
        if ocr.corrupted_document:
            return DocumentState.CORRUPTED_DOCUMENT
        if classification.document_state in {
            DocumentState.NON_MEDICAL_DOCUMENT,
            DocumentState.NON_REFERRAL_MEDICAL,
        }:
            return classification.document_state
        if not validation.is_complete_referral:
            return DocumentState.INCOMPLETE_REFERRAL
        if not classification.evidence.passed_rule_threshold:
            return DocumentState.LOW_CONFIDENCE_REFERRAL
        if classification.llm_available and not classification.evidence.passed_llm_threshold:
            return DocumentState.LOW_CONFIDENCE_REFERRAL
        if classification.llm_available and not classification.evidence.agreement_within_threshold:
            return DocumentState.LOW_CONFIDENCE_REFERRAL
        if ocr.quality.poor_quality:
            return DocumentState.LOW_CONFIDENCE_REFERRAL
        if classification.referral_type == ReferralType.SELF_REFERRAL:
            return DocumentState.SELF_REFERRAL
        if confidence.final_confidence_score < settings.LOW_CONFIDENCE_THRESHOLD:
            return DocumentState.LOW_CONFIDENCE_REFERRAL
        return DocumentState.VALID_REFERRAL

    def _to_percent(self, value: float) -> float:
        # The frontend expects 0-100 percentages, while the backend computes 0-1 normalized scores.
        return round(max(0.0, min(value, 1.0)) * 100, 2)
