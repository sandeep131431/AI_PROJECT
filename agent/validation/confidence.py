
from decimal import Decimal, InvalidOperation


REQUIRED_FIELDS = [
    "invoice_number",
    "invoice_date",
    "vendor_id",
    "vendor_name",
    "currency",
    "subtotal",
    "tax",
    "total_amount",
    "line_items",
]


def calculate_confidence(
    invoice,
    internal_status,
    erp_status,
    translation_confidence
):
    # 1. Required fields: 20 marks
    available = 0

    for field in REQUIRED_FIELDS:
        value = invoice.get(field)

        if field == "line_items":
            if isinstance(value, list) and value:
                available += 1
        elif value is not None and str(value).strip():
            available += 1

    completeness_score = (available / len(REQUIRED_FIELDS)) * 20

    # 2. Internal validation: 25 marks
    internal_score = 25 if internal_status == "PASSED" else 0

    # 3. ERP validation: 35 marks
    erp_score = 35 if erp_status == "PASSED" else 0

    # 4. Translation confidence: 20 marks
    translation_score = 0

    if translation_confidence is not None:
        try:
            value = Decimal(str(translation_confidence))

            # Accept either 0-1 or 0-100 format
            if value > 1:
                value = value / 100

            value = max(Decimal("0"), min(value, Decimal("1")))
            translation_score = float(value * 20)

        except (InvalidOperation, ValueError, TypeError):
            translation_score = 0

    total = (
        completeness_score
        + internal_score
        + erp_score
        + translation_score
    )

    return {
        "confidence_score": round(total, 2),
        "breakdown": {
            "completeness": round(completeness_score, 2),
            "internal_validation": internal_score,
            "erp_validation": erp_score,
            "translation": round(translation_score, 2),
        }
    }
