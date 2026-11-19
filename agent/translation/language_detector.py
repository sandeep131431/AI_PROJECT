
import re
from langchain_aws import ChatBedrockConverse

llm = ChatBedrockConverse(
    model="amazon.nova-lite-v1:0",
    region_name="us-east-1",
    temperature=0
)


def detect_language(raw_text):

    if not raw_text or not raw_text.strip():
        return {
            "language": None,
            "language_code": None,
            "status": "FAILED",
            "error": "Empty text"
        }

    try:
        prompt = f"""
        Identify the language of this invoice.

        Return only language name and ISO 639-1 code.
        Example: German (de)

        Invoice Text:
        {raw_text[:4000]}
        """

        response = llm.invoke(prompt)
        detected = response.content.strip()

        match = re.search(
            r"([A-Za-z]+)\s*\(([a-z]{2})\)",
            detected
        )

        if not match:
            raise ValueError(f"Unexpected response: {detected}")

        return {
            "language": match.group(1),
            "language_code": match.group(2),
            "status": "SUCCESS",
            "error": None
        }

    except Exception as error:
        return {
            "language": None,
            "language_code": None,
            "status": "FAILED",
            "error": str(error)
        }
