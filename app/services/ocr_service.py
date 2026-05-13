import base64
import requests
from PIL import Image
from app.core.config import settings
from app.pipelines.file_handler import FileHandler


class OCRService:

    OCR_MODEL = "glm-ocr:latest"

    BASE_URL = settings.OLLAMA_URL.replace(
        "/api/generate",
        ""
    )

    @staticmethod
    async def extract_text(file):
        """
        Extract text from uploaded file.
        Uses FileHandler to process different file types.
        """

        items = await FileHandler.process_file(file)

        extracted_text = ""

        for item in items:

            if isinstance(item, tuple) and item[0] == "text":
                extracted_text += "\n" + item[1]

            elif isinstance(item, Image.Image):
                image_bytes = FileHandler.image_to_bytes(item)
                text = OCRService.process_image_bytes(image_bytes)
                extracted_text += "\n" + text

        return extracted_text.strip()

    @staticmethod
    def process_image_bytes(image_bytes: bytes) -> str:

        base64_image = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        response = requests.post(
            f"{OCRService.BASE_URL}/api/chat",
            json={
                "model": OCRService.OCR_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": """
Extract all text from this healthcare referral form.
Return plain OCR text only.
""",
                        "images": [base64_image]
                    }
                ],
                "stream": False,
                "options": {
                    "temperature": 0
                }
            },
            timeout=600
        )

        if response.status_code != 200:

            raise Exception(
                f"OCR Error: {response.status_code} - {response.text}"
            )

        result = response.json()

        return result["message"]["content"].strip()