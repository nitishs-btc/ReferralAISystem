class ValidationService:

    REQUIRED_FIELDS = [
        "patient_name",
        "provider_name",
        "referral_reason"
    ]

    @staticmethod
    def validate(data: dict):

        missing_fields = []

        patient = data.get("patient_information", {})
        provider = data.get("provider_information", {})
        clinical = data.get("clinical_information", {})

        # Required validations
        if not patient.get("patient_name"):
            missing_fields.append("patient_name")

        if not provider.get("provider_name"):
            missing_fields.append("provider_name")

        if not clinical.get("referral_reason"):
            missing_fields.append("referral_reason")

        is_complete = len(missing_fields) == 0

        # IMPORTANT FIX
        # If required data missing -> NOT valid referral
        if not is_complete:
            data["is_referral_document"] = False
            data["document_type"] = "Incomplete Referral"

        return {
            "is_complete_referral": is_complete,
            "missing_fields": missing_fields,
            "warnings": [],
            "needs_human_review": not is_complete
        }