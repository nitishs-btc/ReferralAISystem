"""Hybrid classification using rules first and LLM reasoning second, then comparing both outputs."""

from typing import Any

from app.core.config import settings
from app.core.exceptions import LLMServiceError
from app.schemas.referral import (
    ClassificationEvidence,
    ClassificationResult,
    DocumentCategory,
    DocumentState,
    OCRResult,
    ReferralType,
)
from app.services.llm_service import LLMService


class ClassificationService:
    POSITIVE_REFERRAL_KEYWORDS = {
        "referral": 0.22,
        "referred": 0.20,
        "reason for referral": 0.18,
        "specialty": 0.10,
        "provider": 0.06,
        "diagnosis": 0.07,
        "npi": 0.05,
        "fax": 0.05,
        "insurance": 0.04,
        "dob": 0.03,
    }
    SUPPORTING_MEDICAL_KEYWORDS = {
        "member id": 0.16,
        "policy": 0.12,
        "claim": 0.10,
        "insurance card": 0.26,
        "lab result": 0.20,
        "radiology": 0.16,
        "discharge": 0.18,
    }
    NEGATIVE_NON_MEDICAL_KEYWORDS = {
        "invoice": 0.25,
        "receipt": 0.22,
        "bank": 0.20,
        "terms and conditions": 0.16,
        "employment": 0.12,
        "resume": 0.12,
    }
    SELF_REFERRAL_KEYWORDS = {
        "self referral": 0.45,
        "self-referral": 0.45,
        "self referred": 0.40,
        "self-referred": 0.40,
    }

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def classify(self, *, document_id: str, ocr: OCRResult) -> ClassificationResult:
        # Rules always run, even when the LLM is down, so the pipeline can still return a usable result.
        rule_result = self._rule_classification(ocr)
        should_call_llm, llm_skip_reason = self._should_call_llm(rule_result=rule_result, ocr=ocr)
        llm_payload, llm_available = await self._classify_with_llm(
            document_id=document_id,
            ocr=ocr,
            should_call_llm=should_call_llm,
        )

        llm_score = self._safe_float(llm_payload.get("confidence", 0.0)) if llm_payload else 0.0
        rule_score = rule_result["rule_score"]
        passed_rule_threshold = rule_score >= settings.RULE_REFERRAL_THRESHOLD
        passed_llm_threshold = llm_available and llm_score >= settings.LLM_REFERRAL_THRESHOLD
        agreement_score = round(max(0.0, 1.0 - abs(rule_score - llm_score)), 4) if llm_available else 0.0
        agreement_within_threshold = (abs(rule_score - llm_score) <= settings.CLASSIFIER_DISAGREEMENT_THRESHOLD) if llm_available else False
        final_confidence = round((rule_score * 0.45) + (llm_score * 0.55), 4) if llm_available else round(rule_score, 4)

        document_state = self._resolve_state(rule_result, llm_payload, final_confidence)
        document_category = self._resolve_category(rule_result, llm_payload, document_state)
        referral_type = self._resolve_referral_type(rule_result, llm_payload, document_state)
        document_type = self._resolve_document_type(rule_result, llm_payload, document_state)

        return ClassificationResult(
            document_state=document_state,
            document_type=document_type,
            document_category=document_category,
            referral_type=referral_type,
            is_referral_candidate=document_state
            in {
                DocumentState.VALID_REFERRAL,
                DocumentState.INCOMPLETE_REFERRAL,
                DocumentState.SELF_REFERRAL,
                DocumentState.LOW_CONFIDENCE_REFERRAL,
            },
            confidence=final_confidence,
            llm_available=llm_available,
            evidence=ClassificationEvidence(
                rule_score=round(rule_score, 4),
                llm_score=round(llm_score, 4),
                layout_score=rule_result["layout_score"],
                ocr_score=ocr.average_confidence,
                llm_invoked=should_call_llm and llm_available,
                llm_skip_reason=None if should_call_llm else llm_skip_reason,
                passed_rule_threshold=passed_rule_threshold,
                passed_llm_threshold=passed_llm_threshold,
                agreement_score=agreement_score,
                agreement_within_threshold=agreement_within_threshold,
                positive_signals=rule_result["positive_signals"],
                negative_signals=rule_result["negative_signals"],
                explanation=(llm_payload or {}).get("reason", rule_result["reason"]),
            ),
        )

    def _rule_classification(self, ocr: OCRResult) -> dict[str, Any]:
        # The rule engine provides a cheap first-pass signal based on document text and layout cues.
        text = f"{ocr.markdown}\n{ocr.raw_text}".lower()
        if ocr.corrupted_document:
            return {
                "document_state": DocumentState.CORRUPTED_DOCUMENT,
                "rule_score": 0.0,
                "layout_score": 0.0,
                "reason": "Document appears to be corrupted.",
                "positive_signals": [],
                "negative_signals": ["corrupted_document"],
                "document_type": "Corrupted Document",
                "referral_intent_score": 0.0,
            }
        if ocr.blank_document or not text.strip():
            return {
                "document_state": DocumentState.BLANK_DOCUMENT,
                "rule_score": 0.0,
                "layout_score": 0.0,
                "reason": "No OCR text was detected.",
                "positive_signals": [],
                "negative_signals": ["blank_document"],
                "document_type": "Blank Document",
                "referral_intent_score": 0.0,
            }

        referral_score, referral_hits = self._score_keywords(text, self.POSITIVE_REFERRAL_KEYWORDS)
        supporting_score, supporting_hits = self._score_keywords(text, self.SUPPORTING_MEDICAL_KEYWORDS)
        non_medical_score, negative_hits = self._score_keywords(text, self.NEGATIVE_NON_MEDICAL_KEYWORDS)
        self_referral_score, self_referral_hits = self._score_keywords(text, self.SELF_REFERRAL_KEYWORDS)

        checkbox_signal = 0.10 if "[ ]" in text or "[x]" in text or "checkbox" in text else 0.0
        provider_signal = 0.10 if "provider" in text or "referred by" in text else 0.0
        layout_score = min(checkbox_signal + provider_signal, 0.20)

        referral_rule_score = min(referral_score + self_referral_score + layout_score, 1.0)

        # If a negative/non-medical pattern is clearly strongest, short-circuit before referral routing.
        if non_medical_score >= max(referral_rule_score, supporting_score) and non_medical_score >= 0.20:
            return {
                "document_state": DocumentState.NON_MEDICAL_DOCUMENT,
                "rule_score": round(1.0 - non_medical_score, 4),
                "layout_score": round(layout_score, 4),
                "reason": "Rule engine found predominantly non-medical signals.",
                "positive_signals": negative_hits,
                "negative_signals": negative_hits,
                "document_type": self._infer_non_medical_type(text),
                "referral_intent_score": round(referral_rule_score, 4),
            }

        if self_referral_score >= 0.35:
            return {
                "document_state": DocumentState.SELF_REFERRAL,
                "rule_score": round(min(referral_rule_score, 1.0), 4),
                "layout_score": round(layout_score, 4),
                "reason": "Self-referral cues were detected in the document.",
                "positive_signals": referral_hits + self_referral_hits,
                "negative_signals": negative_hits,
                "document_type": "Self Referral Form",
                "referral_intent_score": round(referral_rule_score, 4),
            }

        if referral_rule_score >= 0.42:
            return {
                "document_state": DocumentState.VALID_REFERRAL,
                "rule_score": round(referral_rule_score, 4),
                "layout_score": round(layout_score, 4),
                "reason": "Referral layout and content signals are strong.",
                "positive_signals": referral_hits + self_referral_hits + supporting_hits,
                "negative_signals": negative_hits,
                "document_type": "Referral Form",
                "referral_intent_score": round(referral_rule_score, 4),
            }

        if supporting_score >= 0.20:
            return {
                "document_state": DocumentState.NON_REFERRAL_MEDICAL,
                "rule_score": round(max(0.25, supporting_score), 4),
                "layout_score": round(layout_score, 4),
                "reason": "Medical content detected, but referral-specific cues are weak.",
                "positive_signals": supporting_hits,
                "negative_signals": negative_hits,
                "document_type": self._infer_medical_supporting_type(text),
                "referral_intent_score": round(referral_rule_score, 4),
            }

        return {
            "document_state": DocumentState.LOW_CONFIDENCE_REFERRAL,
            "rule_score": round(max(referral_rule_score, 0.20), 4),
            "layout_score": round(layout_score, 4),
            "reason": "Mixed or weak signals require downstream review.",
            "positive_signals": referral_hits + supporting_hits,
            "negative_signals": negative_hits,
            "document_type": "Uncertain Medical Document",
            "referral_intent_score": round(referral_rule_score, 4),
        }

    async def _classify_with_llm(
        self,
        *,
        document_id: str,
        ocr: OCRResult,
        should_call_llm: bool,
    ) -> tuple[dict[str, Any], bool]:
        if not should_call_llm or not ocr.raw_text.strip():
            return {}, False

        try:
            # The prompt asks the model for a normalized classification response rather than free text.
            payload = await self.llm_service.generate_json(
                prompt_file="classification_prompt.txt",
                document_id=document_id,
                variables={
                    "raw_text": ocr.raw_text[:18000],
                    "markdown": ocr.markdown[:18000],
                },
            )
            return payload, True
        except LLMServiceError:
            return {}, False
        except Exception:
            return {}, False

    def _should_call_llm(self, *, rule_result: dict[str, Any], ocr: OCRResult) -> tuple[bool, str | None]:
        if ocr.corrupted_document:
            return False, "Skipped because the document appears corrupted."
        if ocr.blank_document or not ocr.raw_text.strip():
            return False, "Skipped because OCR returned no usable text."

        alphabetic_character_count = self._count_alphabetic_characters(ocr.raw_text)
        if alphabetic_character_count < settings.MIN_TEXT_ALPHA_CHARS_FOR_LLM:
            return False, (
                f"Skipped because OCR returned only {alphabetic_character_count} alphabetic characters; "
                f"minimum required is {settings.MIN_TEXT_ALPHA_CHARS_FOR_LLM}."
            )

        if settings.USE_RULE_GATE_FOR_LLM:
            if rule_result["document_state"] in {
                DocumentState.NON_MEDICAL_DOCUMENT,
                DocumentState.NON_REFERRAL_MEDICAL,
            }:
                return False, "Skipped because rules identified a non-referral document and USE_RULE_GATE_FOR_LLM is true."

            if (
                rule_result["document_state"] == DocumentState.LOW_CONFIDENCE_REFERRAL
                and rule_result.get("referral_intent_score", 0.0) < settings.RULE_LLM_GATE_THRESHOLD
            ):
                return False, (
                    f"Skipped because referral intent score {rule_result.get('referral_intent_score', 0.0):.2f} "
                    f"is below RULE_LLM_GATE_THRESHOLD {settings.RULE_LLM_GATE_THRESHOLD:.2f}."
                )

        return True, None

    def _resolve_state(self, rule_result: dict[str, Any], llm_payload: dict[str, Any], confidence: float) -> DocumentState:
        if rule_result["document_state"] in {DocumentState.BLANK_DOCUMENT, DocumentState.CORRUPTED_DOCUMENT}:
            return rule_result["document_state"]

        llm_state = llm_payload.get("document_state")
        if llm_state in DocumentState._value2member_map_:
            return DocumentState(llm_state)

        if rule_result["document_state"] in {
            DocumentState.NON_MEDICAL_DOCUMENT,
            DocumentState.NON_REFERRAL_MEDICAL,
            DocumentState.SELF_REFERRAL,
            DocumentState.VALID_REFERRAL,
        }:
            return rule_result["document_state"]

        if confidence < settings.LOW_CONFIDENCE_THRESHOLD:
            return DocumentState.LOW_CONFIDENCE_REFERRAL

        return DocumentState.VALID_REFERRAL

    def _resolve_category(
        self,
        rule_result: dict[str, Any],
        llm_payload: dict[str, Any],
        document_state: DocumentState,
    ) -> DocumentCategory:
        llm_category = llm_payload.get("document_category")
        if llm_category in DocumentCategory._value2member_map_:
            return DocumentCategory(llm_category)
        if document_state in {
            DocumentState.VALID_REFERRAL,
            DocumentState.INCOMPLETE_REFERRAL,
            DocumentState.SELF_REFERRAL,
            DocumentState.LOW_CONFIDENCE_REFERRAL,
        }:
            return DocumentCategory.REFERRAL
        if document_state == DocumentState.NON_REFERRAL_MEDICAL:
            return DocumentCategory.MEDICAL_SUPPORTING_DOCUMENT
        if document_state == DocumentState.NON_MEDICAL_DOCUMENT:
            return DocumentCategory.NON_MEDICAL
        return DocumentCategory.UNKNOWN

    def _resolve_referral_type(
        self,
        rule_result: dict[str, Any],
        llm_payload: dict[str, Any],
        document_state: DocumentState,
    ) -> ReferralType:
        llm_value = llm_payload.get("referral_type")
        if llm_value in ReferralType._value2member_map_:
            return ReferralType(llm_value)
        if document_state == DocumentState.SELF_REFERRAL or rule_result["document_state"] == DocumentState.SELF_REFERRAL:
            return ReferralType.SELF_REFERRAL
        if document_state in {
            DocumentState.VALID_REFERRAL,
            DocumentState.INCOMPLETE_REFERRAL,
            DocumentState.LOW_CONFIDENCE_REFERRAL,
        }:
            return ReferralType.PROVIDER_REFERRAL
        return ReferralType.UNKNOWN

    def _resolve_document_type(
        self,
        rule_result: dict[str, Any],
        llm_payload: dict[str, Any],
        document_state: DocumentState,
    ) -> str:
        if llm_payload.get("document_type"):
            return llm_payload["document_type"]
        if document_state == DocumentState.NON_REFERRAL_MEDICAL:
            return "Medical Supporting Document"
        return rule_result["document_type"]

    def _score_keywords(self, text: str, keywords: dict[str, float]) -> tuple[float, list[str]]:
        # Return both the score and the matched signals so review/debugging can explain the result.
        score = 0.0
        hits: list[str] = []
        for keyword, weight in keywords.items():
            if keyword in text:
                score += weight
                hits.append(keyword)
        return min(score, 1.0), hits

    def _safe_float(self, value: Any) -> float:
        try:
            return min(max(float(value), 0.0), 1.0)
        except (TypeError, ValueError):
            return 0.0

    def _count_alphabetic_characters(self, text: str) -> int:
        return sum(1 for character in text if character.isalpha())

    def _infer_medical_supporting_type(self, text: str) -> str:
        if "insurance card" in text or "member id" in text:
            return "Insurance Card"
        if "lab result" in text or "specimen" in text:
            return "Lab Result"
        if "radiology" in text or "impression" in text:
            return "Radiology Report"
        if "discharge" in text:
            return "Discharge Summary"
        return "Medical Supporting Document"

    def _infer_non_medical_type(self, text: str) -> str:
        if "invoice" in text:
            return "Invoice"
        if "receipt" in text:
            return "Receipt"
        if "resume" in text:
            return "Resume"
        if "employment" in text:
            return "Employment Document"
        return "Non Medical Document"
