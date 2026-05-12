import os
import tempfile

from PIL import Image
from pdf2image import convert_from_path
import pytesseract


class OCRService:

    @staticmethod
    async def extract_text(file):

        suffix = file.filename.split(".")[-1]

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        extracted_text = ""

        try:

            if suffix.lower() == "pdf":

                pages = convert_from_path(temp_path)

                for page in pages:
                    text = pytesseract.image_to_string(page)
                    extracted_text += " " + text

            else:

                image = Image.open(temp_path)
                extracted_text = pytesseract.image_to_string(image)

        finally:
            os.remove(temp_path)

        return extracted_text.strip()