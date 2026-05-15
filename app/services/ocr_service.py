from pathlib import Path
import tempfile

from docling.document_converter import DocumentConverter

from app.pipelines.file_handler import FileHandler


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

            markdown_output = document.export_to_markdown()

            text_output = document.export_to_text()

            return {
                "raw_text": text_output,
                "markdown": markdown_output
            }

        finally:

            Path(temp_path).unlink(
                missing_ok=True
            )