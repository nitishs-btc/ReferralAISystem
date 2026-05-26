"""Combines OCR, rule, LLM, extraction, and validation signals into one review-oriented score."""

from statistics import mean
from app.schemas.referral import DocumentState
from app.core.config import settings
from app.schemas.referral import ClassificationResult, ConfidenceFusionResult, ExtractedReferralData, OCRResult, ValidationInformation, DocumentState


class ConfidenceFusionService:
    def fuse(
        self,
        *,
        classification: ClassificationResult,
        extracted_data: ExtractedReferralData,
        validation: ValidationInformation,
        ocr: OCRResult,
    ) -> ConfidenceFusionResult:
        # Extraction confidence is averaged from the field-level confidences collected downstream.
        extraction_confidence = mean(
            extracted_data.confidence_scores.values()) if extracted_data.confidence_scores else 0.0
        rule_score = classification.evidence.rule_score
        llm_score = classification.evidence.llm_score if classification.llm_available else rule_score
        disagreement = abs(rule_score - llm_score)

        components = {
            "ocr": ocr.average_confidence,
            "rule": rule_score,
            "llm": llm_score,
            "extraction": extraction_confidence,
            "validation": validation.validation_confidence,
        }

        final_score = (
                (components["ocr"] * settings.OCR_WEIGHT)
                + (components["rule"] * settings.RULE_WEIGHT)
                + (components["llm"] * settings.LLM_WEIGHT)
                + (components["extraction"] * settings.EXTRACTION_WEIGHT)
                + (components["validation"] * settings.VALIDATION_WEIGHT)
        )

        is_valid_referral = classification.document_state == DocumentState.VALID_REFERRAL
        is_incomplete_referral = classification.document_state == DocumentState.INCOMPLETE_REFERRAL

        # Normalize threshold — .env may store as 0-100 or 0-1
        consider_threshold = settings.CONSIDER_FOR_HUMAN_REVIEW
        if consider_threshold > 1:
            consider_threshold = consider_threshold / 100.0

        review_threshold = settings.REVIEW_CONFIDENCE_THRESHOLD
        if review_threshold > 1:
            review_threshold = review_threshold / 100.0

        needs_review = (
                final_score < review_threshold  # low fused confidence
                or disagreement > settings.CLASSIFIER_DISAGREEMENT_THRESHOLD  # rule vs llm disagree
                or ocr.quality.poor_quality  # bad scan
                or (is_valid_referral and final_score < consider_threshold)  # valid but low confidence
                or (is_incomplete_referral and final_score > settings.LOW_CONFIDENCE_THRESHOLD)  # always review incomplete
        )

        return ConfidenceFusionResult(
            final_confidence_score=round(final_score, 4),
            component_scores={key: round(value, 4) for key, value in components.items()},
            classifier_disagreement=round(disagreement, 4),
            needs_human_review=needs_review,
        )
