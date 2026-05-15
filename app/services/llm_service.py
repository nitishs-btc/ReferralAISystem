import json
import requests

from app.core.config import settings


class LLMService:

    @staticmethod
    def analyze_document(ocr_result: dict):

        """
        LLM semantic extraction layer.

        Receives:
        - markdown
        - raw text

        Performs:
        - contextual extraction
        - semantic mapping
        - classification
        - validation reasoning
        """

        with open(
            "app/prompts/referral_prompt.txt",
            "r"
        ) as file:

            base_prompt = file.read()

        markdown = ocr_result.get(
            "markdown",
            ""
        )

        raw_text = ocr_result.get(
            "raw_text",
            ""
        )

        prompt = f"""
{base_prompt}

DOCUMENT MARKDOWN:
{markdown}

RAW DOCUMENT TEXT:
{raw_text}
"""

        try:

            response = requests.post(
                settings.OLLAMA_URL,
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0,
                        "num_ctx": 8192
                    }
                },
                timeout=300
            )

            response.raise_for_status()

            result = response.json()

            raw_response = result.get(
                "response",
                "{}"
            )

            parsed_response = json.loads(
                raw_response
            )

            return parsed_response

        except json.JSONDecodeError:

            return {
                "error": "Invalid JSON returned from model",
                "raw_response": raw_response,
                "is_referral_document": False,
                "document_type": "Parsing Error"
            }

        except requests.RequestException as e:

            return {
                "error": "LLM request failed",
                "details": str(e),
                "is_referral_document": False,
                "document_type": "LLM Error"
            }

        except Exception as e:

            return {
                "error": "Unexpected error",
                "details": str(e),
                "is_referral_document": False,
                "document_type": "System Error"
            }