from app.schemas.referral import (
    ClassificationResult,
    DocumentState,
    ExtractedReferralData,
    OCRResult,
    ReferralType,
    ValidationInformation,
)


class ValidationService:
    def validate(
        self,
        *,
        classification: ClassificationResult,
        extracted_data: ExtractedReferralData,
        ocr: OCRResult,
    ) -> ValidationInformation:
        if classification.document_state in {
            DocumentState.BLANK_DOCUMENT,
            DocumentState.CORRUPTED_DOCUMENT,
            DocumentState.NON_MEDICAL_DOCUMENT,
            DocumentState.NON_REFERRAL_MEDICAL,
        }:
            return ValidationInformation(
                is_complete_referral=False,
                missing_fields=[],
                warnings=["Document is not a referral candidate."],
                needs_human_review=False,
                validation_confidence=0.85,
                applied_rule_profile="non_referral",
            )

        required_fields = ["patient_name", "referral_reason"]
        profile = "self_referral" if classification.referral_type == ReferralType.SELF_REFERRAL else "provider_referral"
        if profile == "provider_referral":
            required_fields.append("provider_name")

        missing_fields: list[str] = []
        warnings: list[str] = []

        if not extracted_data.patient_information.patient_name:
            missing_fields.append("patient_name")
        if profile == "provider_referral" and not extracted_data.provider_information.provider_name:
            missing_fields.append("provider_name")
        if not extracted_data.clinical_information.referral_reason:
            missing_fields.append("referral_reason")

        if not extracted_data.insurance_information.insurance_name:
            warnings.append("Insurance information missing or not confidently extracted.")
        if ocr.quality.poor_quality:
            warnings.append("OCR quality is poor and may impact extraction accuracy.")

        found_required_fields_count = len(required_fields) - len(missing_fields)
        completeness = found_required_fields_count
        validation_confidence = max(completeness / max(len(required_fields), 1), 0.0)
        needs_human_review = bool(missing_fields) or ocr.quality.poor_quality

        return ValidationInformation(
            is_complete_referral=not missing_fields,
            missing_fields=missing_fields,
            warnings=warnings,
            needs_human_review=needs_human_review,
            validation_confidence=round(validation_confidence, 4),
            completeness_score=round(validation_confidence, 4),
            required_fields_count=len(required_fields),
            found_required_fields_count=found_required_fields_count,
            applied_rule_profile=profile,
        )
