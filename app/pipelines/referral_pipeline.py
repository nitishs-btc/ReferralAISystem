from app.services.ocr_service import OCRService
from app.services.llm_service import LLMService
from app.services.validation_service import ValidationService


class ReferralPipeline:

    @staticmethod
    async def process(file):

        # Step 1 — OCR
        extracted_text = await OCRService.extract_text(file)

        # Step 2 — LLM Structured Extraction
        extracted_data = LLMService.analyze_document(
            extracted_text
        )

        # Step 3 — Validation
        validation_result = ValidationService.validate(
            extracted_data
        )

        extracted_data["validation"] = validation_result

        return {
            "analysis": extracted_data
        }