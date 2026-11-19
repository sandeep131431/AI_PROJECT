
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage


llm = ChatBedrockConverse(
    model="amazon.nova-lite-v1:0",
    region_name="us-east-1",
    temperature=0
)


def translate_to_english(raw_text, language):

    if not raw_text or not raw_text.strip():
        return {
            "translated_text": None,
            "status": "FAILED",
            "error": "Empty text"
        }

    if language.lower() in ["english", "en"]:
        return {
            "translated_text": raw_text,
            "status": "SKIPPED",
            "error": None
        }

    try:
        messages = [
            SystemMessage(content="""
            You are a professional invoice translator.

            Translate the given invoice text into English.

            Important rules:
            1. Preserve invoice numbers.
            2. Preserve vendor names.
            3. Preserve dates and amounts.
            4. Preserve currency symbols and codes.
            5. Do not summarize or remove any information.
            6. Return only translated text.
            """),

            HumanMessage(content=f"""
            Source Language: {language}

            Invoice Text:
            {raw_text}
            """)
        ]

        response = llm.invoke(messages)

        return {
            "translated_text": response.content,
            "status": "SUCCESS",
            "error": None
        }

    except Exception as error:
        return {
            "translated_text": None,
            "status": "FAILED",
            "error": str(error)
        }
