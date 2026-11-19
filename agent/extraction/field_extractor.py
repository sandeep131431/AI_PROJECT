
import json
import re

from langchain_aws import ChatBedrockConverse


llm = ChatBedrockConverse(
    model="amazon.nova-lite-v1:0",
    region_name="us-east-1",
    temperature=0
)


def extract_invoice_fields(translated_text: str):

    if not translated_text or not translated_text.strip():
        return {
            "invoice_data": None,
            "status": "FAILED",
            "error": "Empty invoice text"
        }

    try:

        prompt = f"""
You are an invoice data extraction system.

Extract invoice information from the given text.

Return ONLY valid JSON.
Do not include markdown or explanations.

Rules:
1. Do not guess missing values.
2. Use null for missing fields.
3. Convert dates to YYYY-MM-DD format.
4. Amounts and quantities must be numbers.
5. Preserve every line item.
6. Do not calculate or modify invoice amounts.
7. Keep the original extracted information accurate.

Required JSON structure:

{{
    "invoice_number": null,
    "invoice_date": null,
    "vendor_name": null,
    "vendor_id": null,
    "po_number": null,
    "currency": null,
    "subtotal": null,
    "tax": null,
    "total_amount": null,
    "line_items": [
        {{
            "item_code": null,
            "description": null,
            "quantity": null,
            "unit_price": null,
            "line_total": null
        }}
    ]
}}

Invoice text:
{translated_text}
"""

        response = llm.invoke(prompt)

        content = response.content

        if isinstance(content, list):
            content = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict)
            )

        content = content.strip()

        # Remove markdown JSON formatting if returned by model
        content = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            content,
            flags=re.IGNORECASE
        ).strip()

        invoice_data = json.loads(content)

        if not isinstance(invoice_data, dict):
            raise ValueError("Invalid JSON structure")

        required_fields = [
            "invoice_number",
            "invoice_date",
            "vendor_name",
            "vendor_id",
            "po_number",
            "currency",
            "subtotal",
            "tax",
            "total_amount",
            "line_items"
        ]

        for field in required_fields:
            if field not in invoice_data:
                raise ValueError(f"Missing JSON field: {field}")

        if not isinstance(invoice_data["line_items"], list):
            raise ValueError("line_items must be a list")

        return {
            "invoice_data": invoice_data,
            "status": "SUCCESS",
            "error": None
        }

    except Exception as error:

        return {
            "invoice_data": None,
            "status": "FAILED",
            "error": str(error)
        }
