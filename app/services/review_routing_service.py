"""Converts confidence and validation signals into a human-review decision with explicit reasons."""

from app.core.config import settings
from app.schemas.referral import (
    ClassificationResult,
    ConfidenceFusionResult,
    DocumentState,
    OCRResult,
    ReviewPriority,
    ReviewRoutingResult,
    ValidationInformation,
)


class ReviewRoutingService:
    def route(
        self,
        *,
        classification: ClassificationResult,
        confidence: ConfidenceFusionResult,
        validation: ValidationInformation,
        ocr: OCRResult,
    ) -> ReviewRoutingResult:
        # Review reasons are user-facing/debug-facing explanations, so keep them specific and actionable.
        reasons: list[str] = []

        if confidence.final_confidence_score < settings.REVIEW_CONFIDENCE_THRESHOLD:
            reasons.append("Final confidence below straight-through threshold.")
        if confidence.classifier_disagreement > settings.CLASSIFIER_DISAGREEMENT_THRESHOLD:
            reasons.append("Rule engine and LLM classification disagree materially.")
        if not classification.evidence.passed_rule_threshold:
            reasons.append("Rule score did not pass referral threshold.")
        if classification.llm_available and not classification.evidence.passed_llm_threshold:
            reasons.append("LLM score did not pass referral threshold.")
        if validation.missing_fields:
            reasons.append(f"Required fields missing: {', '.join(validation.missing_fields)}.")
        if ocr.quality.poor_quality:
            reasons.append("OCR quality is below acceptable threshold.")
        if classification.document_state == DocumentState.LOW_CONFIDENCE_REFERRAL:
            reasons.append("Document remained in a low-confidence referral state.")
        # if confidence.needs_human_review and not reasons:
        #     reasons.append("Confidence fusion flagged for human review.")

        if not reasons:
            return ReviewRoutingResult(
                needs_human_review=False,
                priority=ReviewPriority.LOW,
                queue="straight_through",
                reasons=[],
            )

        priority = ReviewPriority.MEDIUM
        if ocr.quality.poor_quality or len(validation.missing_fields) >= 2:
            priority = ReviewPriority.HIGH

        return ReviewRoutingResult(
            needs_human_review=True,
            priority=priority,
            queue="human_review",
            reasons=reasons,
        )
