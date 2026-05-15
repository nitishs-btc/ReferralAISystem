import asyncio
from typing import List

from fastapi import UploadFile

from app.services.ocr_service import OCRService
from app.services.llm_service import LLMService
from app.services.validation_service import ValidationService

from app.pipelines.file_handler import FileHandler


MAX_CONCURRENT = 2


class ReferralPipeline:

    @staticmethod
    async def process(file):

        # OCR
        ocr_result = await OCRService.extract_document(
            file
        )

        # LLM Extraction
        extracted_data = LLMService.analyze_document(
            ocr_result
        )

        # Validation
        validation_result = ValidationService.validate(
            extracted_data
        )

        extracted_data["validation"] = validation_result

        return {
            "raw_text": ocr_result["raw_text"],
            "markdown": ocr_result["markdown"],
            "extracted_data": extracted_data
        }

    @staticmethod
    async def process_batch(files: List[UploadFile]):

        semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        async def process_single_upload(file):

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

        tasks = [
            process_single_upload(file)
            for file in files
        ]

        all_results = await asyncio.gather(*tasks)

        results = []

        for file_results in all_results:
            results.extend(file_results)

        successful = sum(
            1 for r in results
            if r["status"] == "success"
        )

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
    async def process_archive(file):

        try:

            extracted_files = await FileHandler.extract_archive(file)

            semaphore = asyncio.Semaphore(MAX_CONCURRENT)

            async def process_single(filename, content):

                async with semaphore:

                    return await ReferralPipeline.process_single_file(
                        filename,
                        content
                    )

            tasks = [
                process_single(filename, content)
                for filename, content in extracted_files
            ]

            results = await asyncio.gather(*tasks)

            successful = sum(
                1 for r in results
                if r["status"] == "success"
            )

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
    async def process_single_file(
        filename: str,
        content: bytes
    ):

        file_result = {
            "filename": filename,
            "status": "success",
            "data": None,
            "error": None
        }

        try:

            ocr_result = await ReferralPipeline.process_content(
                filename,
                content
            )

            extracted_data = LLMService.analyze_document(
                ocr_result
            )

            validation_result = ValidationService.validate(
                extracted_data
            )

            extracted_data["validation"] = validation_result

            file_result["data"] = {
                "raw_text": ocr_result["raw_text"],
                "markdown": ocr_result["markdown"],
                "extracted_data": extracted_data
            }

        except Exception as e:

            file_result["status"] = "error"
            file_result["error"] = str(e)

        return file_result

    @staticmethod
    async def process_content(
        filename: str,
        content: bytes
    ):

        from PIL import Image

        items = FileHandler.process_extracted_content(
            filename,
            content
        )

        all_blocks = []

        page_number = 1

        for item in items:

            if isinstance(item, tuple) and item[0] == "text":

                all_blocks.append({
                    "id": len(all_blocks) + 1,
                    "page": page_number,
                    "line": 1,
                    "text": item[1],
                    "bbox": None,
                    "confidence": 1.0
                })

            elif isinstance(item, Image.Image):

                blocks = OCRService.process_image(
                    item,
                    page_number
                )

                all_blocks.extend(blocks)

            page_number += 1

        raw_text = OCRService.build_raw_text(
            all_blocks
        )

        return {
            "raw_text": raw_text,
            "ocr_blocks": all_blocks
        }