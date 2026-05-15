from pathlib import Path
import tempfile

from docling.document_converter import DocumentConverter


class OCRService:

    converter = DocumentConverter()

    @staticmethod
    async def extract_document(file):

        suffix = Path(file.filename).suffix

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:

            content = await file.read()

            temp_file.write(content)

            temp_path = temp_file.name

        try:

            result = OCRService.converter.convert(
                temp_path
            )

            document = result.document

            full_markdown = document.export_to_markdown()

            full_text = document.export_to_text()

            total_pages = len(document.pages)

            return {
                "raw_text": full_text,
                "markdown": full_markdown,
                "total_pages": total_pages
            }

        finally:

            Path(temp_path).unlink(
                missing_ok=True
            )