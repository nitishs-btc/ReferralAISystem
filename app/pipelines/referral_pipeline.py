from typing import List
from fastapi import UploadFile
from app.services.ocr_service import OCRService
from app.services.llm_service import LLMService
from app.services.validation_service import ValidationService
from app.pipelines.file_handler import FileHandler


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

        return extracted_data

    @staticmethod
    async def process_batch(files: List[UploadFile]) -> dict:
        """
        Process multiple files (folder upload, ZIP, TAR).
        Returns results array with status for each file.
        """

        results = []
        successful = 0
        failed = 0

        for file in files:

            if FileHandler.is_archive(file.filename):
                archive_results = await ReferralPipeline.process_archive(file)
                for res in archive_results["results"]:
                    results.append(res)
                    if res["status"] == "success":
                        successful += 1
                    else:
                        failed += 1
                continue

            file_result = {
                "filename": file.filename,
                "status": "success",
                "data": None,
                "error": None
            }

            try:

                if not FileHandler.is_supported(file.filename):
                    file_result["status"] = "skipped"
                    file_result["error"] = "Unsupported file type"
                    failed += 1
                    results.append(file_result)
                    continue

                data = await ReferralPipeline.process(file)
                file_result["data"] = data
                successful += 1

            except Exception as e:
                file_result["status"] = "error"
                file_result["error"] = str(e)
                failed += 1

            results.append(file_result)

        return {
            "summary": {
                "total_files": len(results),
                "successful": successful,
                "failed": failed
            },
            "results": results
        }

    @staticmethod
    async def process_archive(file) -> dict:
        """
        Process ZIP or TAR archive.
        Extracts files and processes each one.
        """

        results = []
        successful = 0
        failed = 0

        try:
            extracted_files = await FileHandler.extract_archive(file)

            for filename, content in extracted_files:

                file_result = {
                    "filename": filename,
                    "status": "success",
                    "data": None,
                    "error": None
                }

                try:
                    extracted_text = await ReferralPipeline.process_content(filename, content)

                    extracted_data = LLMService.analyze_document(extracted_text)

                    validation_result = ValidationService.validate(extracted_data)
                    extracted_data["validation"] = validation_result

                    file_result["data"] = extracted_data
                    successful += 1

                except Exception as e:
                    file_result["status"] = "error"
                    file_result["error"] = str(e)
                    failed += 1

                results.append(file_result)

        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "data": None,
                "error": f"Archive extraction failed: {str(e)}"
            })
            failed += 1

        return {
            "summary": {
                "total_files": len(results),
                "successful": successful,
                "failed": failed
            },
            "results": results
        }

    @staticmethod
    async def process_content(filename: str, content: bytes) -> str:
        """Process file content directly (for extracted archive files)."""

        from PIL import Image

        items = FileHandler.process_extracted_content(filename, content)

        extracted_text = ""

        for item in items:

            if isinstance(item, tuple) and item[0] == "text":
                extracted_text += "\n" + item[1]

            elif isinstance(item, Image.Image):
                image_bytes = FileHandler.image_to_bytes(item)
                text = OCRService.process_image_bytes(image_bytes)
                extracted_text += "\n" + text

        return extracted_text.strip()