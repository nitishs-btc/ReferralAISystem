import asyncio
from typing import List
from fastapi import UploadFile
from app.services.ocr_service import OCRService
from app.services.llm_service import LLMService
from app.services.validation_service import ValidationService
from app.pipelines.file_handler import FileHandler

MAX_CONCURRENT = 5


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
        Process multiple files (folder upload, ZIP, TAR) in parallel.
        Returns results array with status for each file.
        """

        semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        async def process_single_upload(file: UploadFile) -> List[dict]:

            if FileHandler.is_archive(file.filename):
                archive_results = await ReferralPipeline.process_archive(file)
                return archive_results["results"]

            file_result = {
                "filename": file.filename,
                "status": "success",
                "data": None,
                "error": None
            }

            if not FileHandler.is_supported(file.filename):
                file_result["status"] = "skipped"
                file_result["error"] = "Unsupported file type"
                return [file_result]

            try:
                async with semaphore:
                    data = await ReferralPipeline.process(file)
                    file_result["data"] = data

            except Exception as e:
                file_result["status"] = "error"
                file_result["error"] = str(e)

            return [file_result]

        tasks = [process_single_upload(file) for file in files]
        all_results = await asyncio.gather(*tasks)

        results = []
        for file_results in all_results:
            results.extend(file_results)

        successful = sum(1 for r in results if r["status"] == "success")
        failed = len(results) - successful

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
        Extracts files and processes each one in parallel.
        """

        try:
            extracted_files = await FileHandler.extract_archive(file)

            semaphore = asyncio.Semaphore(MAX_CONCURRENT)

            async def process_single(filename: str, content: bytes) -> dict:
                async with semaphore:
                    return await ReferralPipeline.process_single_file(filename, content)

            tasks = [
                process_single(filename, content)
                for filename, content in extracted_files
            ]

            results = await asyncio.gather(*tasks)

            successful = sum(1 for r in results if r["status"] == "success")
            failed = len(results) - successful

            return {
                "summary": {
                    "total_files": len(results),
                    "successful": successful,
                    "failed": failed
                },
                "results": list(results)
            }

        except Exception as e:
            return {
                "summary": {
                    "total_files": 1,
                    "successful": 0,
                    "failed": 1
                },
                "results": [{
                    "filename": file.filename,
                    "status": "error",
                    "data": None,
                    "error": f"Archive extraction failed: {str(e)}"
                }]
            }

    @staticmethod
    async def process_single_file(filename: str, content: bytes) -> dict:
        """Process a single file from archive."""

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

        except Exception as e:
            file_result["status"] = "error"
            file_result["error"] = str(e)

        return file_result

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