import json
import requests

from app.core.config import settings


class LLMService:

    @staticmethod
    def analyze_document(document_text: str):

        # Load base prompt
        with open("app/prompts/referral_prompt.txt", "r") as file:
            base_prompt = file.read()

        # Final prompt
        prompt = f"""
{base_prompt}

DOCUMENT:
{document_text}
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
                        "temperature": 3
                    }
                },
                timeout=300
            )

            response.raise_for_status()

            result = response.json()

            raw_response = result.get("response", "")

            # Parse model JSON response
            parsed_response = json.loads(raw_response)

            return parsed_response

        except json.JSONDecodeError:

            return {
                "error": "Invalid JSON returned from model",
                "raw_response": raw_response
            }

        except requests.RequestException as e:

            return {
                "error": "LLM request failed",
                "details": str(e)
            }

        except Exception as e:

            return {
                "error": "Unexpected error",
                "details": str(e)
            }