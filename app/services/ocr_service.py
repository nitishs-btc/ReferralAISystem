import base64
import io
import requests
from pdf2image import convert_from_bytes
from app.core.config import settings


class OCRService:

    OCR_MODEL = "glm-ocr:latest"

    BASE_URL = settings.OLLAMA_URL.replace(
        "/api/generate",
        ""
    )

    @staticmethod
    async def extract_text(file):

        content = await file.read()

        filename = file.filename.lower()

        extracted_text = ""

        if filename.endswith(".pdf"):

            pages = convert_from_bytes(
                content,
                dpi=100
            )

            for page in pages[:1]:

                text = OCRService.process_pil_image(
                    page
                )

                extracted_text += "\n" + text

        else:

            extracted_text = OCRService.process_raw_bytes(
                content
            )

        return extracted_text.strip()

    @staticmethod
    def process_pil_image(image):

        buffer = io.BytesIO()

        image = image.convert("RGB")

        # Smaller image
        max_size = (700, 700)

        image.thumbnail(max_size)

        image.save(
            buffer,
            format="JPEG",
            quality=60
        )

        image_bytes = buffer.getvalue()

        return OCRService.process_raw_bytes(
            image_bytes
        )

    @staticmethod
    def process_raw_bytes(image_bytes):

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