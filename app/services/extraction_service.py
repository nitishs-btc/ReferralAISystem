"""Structured entity extraction that merges regex-based parsing with optional LLM enrichment."""

import re
from typing import Any

from app.core.exceptions import LLMServiceError
from app.schemas.referral import (
    ClassificationResult,
    ClinicalInformation,
    DocumentCategory,
    ExtractedReferralData,
    InsuranceInformation,
    OCRResult,
    PatientInformation,
    ProviderInformation,
    ReferralType,
)
from app.services.llm_service import LLMService


class ExtractionService:
    ICD_PATTERN = re.compile(r"\b[A-TV-Z][0-9][0-9AB](?:\.[0-9A-TV-Z]{1,4})?\b")
    CPT_PATTERN = re.compile(r"\b\d{5}\b")
    PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
    DOB_PATTERN = re.compile(r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b")

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def extract(
        self,
        *,
        document_id: str,
        classification: ClassificationResult,
        ocr: OCRResult,
    ) -> ExtractedReferralData:
        # Regex extraction gives a fast baseline even when the LLM is unavailable.
        regex_payload = self._regex_extract(ocr.raw_text)
        llm_payload = await self._extract_with_llm(document_id=document_id, classification=classification, ocr=ocr)
        merged = self._merge_payloads(classification, regex_payload, llm_payload)
        return ExtractedReferralData.model_validate(merged)

    async def _extract_with_llm(
        self,
        *,
        document_id: str,
        classification: ClassificationResult,
        ocr: OCRResult,
    ) -> dict[str, Any]:
        if not ocr.raw_text.strip():
            return {}

        try:
            return await self.llm_service.generate_json(
                prompt_file="extraction_prompt.txt",
                document_id=document_id,
                variables={
                    "document_state": classification.document_state.value,
                    "document_type": classification.document_type,
                    "document_category": classification.document_category.value,
                    "referral_type": classification.referral_type.value,
                    "raw_text": ocr.raw_text[:24000],
                    "markdown": ocr.markdown[:24000],
                },
            )
        except LLMServiceError:
            return {}
        except Exception:
            return {}

    def _regex_extract(self, text: str) -> dict[str, Any]:
        # Regex is intentionally limited to deterministic fields that do not need semantic reasoning.
        phones = self.PHONE_PATTERN.findall(text)
        dob = self.DOB_PATTERN.search(text)
        icd_codes = sorted(set(self.ICD_PATTERN.findall(text)))
        cpt_codes = sorted(set(self.CPT_PATTERN.findall(text)))

        return {
            "patient_information": {
                "dob": dob.group(0) if dob else None,
                "phone": phones[0] if phones else None,
            },
            "provider_information": {
                "provider_phone": phones[1] if len(phones) > 1 else None,
                "provider_fax": phones[2] if len(phones) > 2 else None,
            },
            "clinical_information": {
                "icd_codes": icd_codes[:20],
                "cpt_codes": cpt_codes[:20],
            },
        }

    def _merge_payloads(
        self,
        classification: ClassificationResult,
        regex_payload: dict[str, Any],
        llm_payload: dict[str, Any],
    ) -> dict[str, Any]:
        # LLM fields override regex only when they contain a usable non-empty value.
        patient = self._merged_section(PatientInformation(), regex_payload.get("patient_information"), llm_payload.get("patient_information"))
        provider = self._merged_section(ProviderInformation(), regex_payload.get("provider_information"), llm_payload.get("provider_information"))
        insurance = self._merged_section(InsuranceInformation(), {}, llm_payload.get("insurance_information"))
        clinical = self._merged_section(ClinicalInformation(), regex_payload.get("clinical_information"), llm_payload.get("clinical_information"))

        llm_confidence = llm_payload.get("confidence_scores", {}) or {}
        extracted_confidence = {
            "patient_name": self._normalize_field_confidence(llm_confidence.get("patient_name"), patient.patient_name),
            "dob": self._normalize_field_confidence(llm_confidence.get("dob"), patient.dob),
            "gender": self._normalize_field_confidence(llm_confidence.get("gender"), patient.gender),
            "phone": self._normalize_field_confidence(llm_confidence.get("phone"), patient.phone),
            "provider_name": self._normalize_field_confidence(llm_confidence.get("provider_name"), provider.provider_name),
            "provider_phone": self._normalize_field_confidence(llm_confidence.get("provider_phone"), provider.provider_phone),
            "provider_fax": self._normalize_field_confidence(llm_confidence.get("provider_fax"), provider.provider_fax),
            "insurance_name": self._normalize_field_confidence(llm_confidence.get("insurance_name"), insurance.insurance_name),
            "member_id": self._normalize_field_confidence(llm_confidence.get("member_id"), insurance.member_id),
            "referral_reason": self._normalize_field_confidence(llm_confidence.get("referral_reason"), clinical.referral_reason),
            "specialty": self._normalize_field_confidence(llm_confidence.get("specialty"), clinical.specialty),
            "priority": self._normalize_field_confidence(llm_confidence.get("priority"), clinical.priority),
            "diagnosis": self._normalize_field_confidence(llm_confidence.get("diagnosis"), clinical.diagnosis),
            "icd_codes": self._normalize_field_confidence(llm_confidence.get("icd_codes"), clinical.icd_codes),
            "cpt_codes": self._normalize_field_confidence(llm_confidence.get("cpt_codes"), clinical.cpt_codes),
        }

        is_referral_document = classification.document_category == DocumentCategory.REFERRAL
        return {
            "is_referral_document": is_referral_document,
            "document_type": llm_payload.get("document_type") or classification.document_type,
            "document_category": classification.document_category.value,
            "referral_type": (
                llm_payload.get("referral_type")
                if llm_payload.get("referral_type") in ReferralType._value2member_map_
                else classification.referral_type.value
            ),
            "patient_information": patient.model_dump(),
            "provider_information": provider.model_dump(),
            "insurance_information": insurance.model_dump(),
            "clinical_information": clinical.model_dump(),
            "validation": llm_payload.get("validation", {}),
            "confidence_scores": extracted_confidence,
        }

    def _merged_section(self, model: Any, regex_values: dict[str, Any] | None, llm_values: dict[str, Any] | None):
        merged = model.model_dump()
        for source in (regex_values or {}, llm_values or {}):
            for key, value in source.items():
                if value not in (None, "", []):
                    merged[key] = value
        return model.__class__.model_validate(merged)

    def _normalize_field_confidence(self, value: Any, field_value: Any) -> float:
        # When the LLM is absent, fields extracted by regex still get a moderate confidence instead of 0.
        if value is None:
            return 0.75 if field_value not in (None, "", []) else 0.0
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.75 if field_value not in (None, "", []) else 0.0
        if numeric > 1:
            numeric = numeric / 100.0
        return min(max(numeric, 0.0), 1.0)
