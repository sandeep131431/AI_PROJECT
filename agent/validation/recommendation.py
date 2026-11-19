
def generate_recommendation(
    confidence_score,
    internal_status,
    erp_status,
    discrepancies
):
    discrepancies = discrepancies or []

    # Confirmed invalid currency is a rejection condition
    invalid_currency = any(
        item.get("field_name") == "currency"
        and item.get("erp_value") == "Currency not accepted"
        for item in discrepancies
    )

    if invalid_currency:
        return {
            "recommendation": "reject",
            "reason": "Invoice currency is not accepted"
        }

    # Any validation failure or discrepancy requires auditor review
    if (
        internal_status != "PASSED"
        or erp_status != "PASSED"
        or discrepancies
    ):
        return {
            "recommendation": "manual review",
            "reason": "Validation failed or discrepancies detected"
        }

    if confidence_score >= 95:
        return {
            "recommendation": "approve",
            "reason": "All validations passed with high confidence"
        }

    return {
        "recommendation": "manual review",
        "reason": "Confidence score is below approval threshold"
    }
