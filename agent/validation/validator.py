
from decimal import Decimal, InvalidOperation


def to_decimal(value):

    try:
        if value is None:
            return None

        return Decimal(str(value))

    except (InvalidOperation, ValueError, TypeError):
        return None


# 1. Required Fields Validation

def validate_required_fields(invoice):

    errors = []

    required_fields = [
        "invoice_number",
        "invoice_date",
        "vendor_name",
        "currency",
        "subtotal",
        "tax",
        "total_amount"
    ]

    for field in required_fields:

        value = invoice.get(field)

        if value is None or str(value).strip() == "":
            errors.append(f"Missing required field: {field}")

    return errors


# 2. Line Items Validation

def validate_invoice_items(line_items):

    errors = []
    calculated_subtotal = Decimal("0")

    if not isinstance(line_items, list) or not line_items:
        return ["Invoice line items are missing"], calculated_subtotal

    for index, item in enumerate(line_items, start=1):

        if not isinstance(item, dict):
            errors.append(f"Item {index}: Invalid item format")
            continue

        quantity = to_decimal(item.get("quantity"))
        unit_price = to_decimal(item.get("unit_price"))
        line_total = to_decimal(item.get("line_total"))

        if quantity is None:
            errors.append(f"Item {index}: Invalid quantity")
            continue

        if unit_price is None:
            errors.append(f"Item {index}: Invalid unit price")
            continue

        if line_total is None:
            errors.append(f"Item {index}: Invalid line total")
            continue

        if quantity <= 0:
            errors.append(f"Item {index}: Quantity must be greater than zero")

        if unit_price < 0:
            errors.append(f"Item {index}: Unit price cannot be negative")

        if line_total < 0:
            errors.append(f"Item {index}: Line total cannot be negative")

        expected_line_total = quantity * unit_price

        if expected_line_total.quantize(Decimal("0.01")) != line_total.quantize(Decimal("0.01")):

            errors.append(
                f"Item {index}: Line total mismatch. "
                f"Expected {expected_line_total}, Found {line_total}"
            )

        calculated_subtotal += expected_line_total

    return errors, calculated_subtotal


# 3. Subtotal Validation

def validate_subtotal(calculated_subtotal, invoice_subtotal):

    errors = []

    subtotal = to_decimal(invoice_subtotal)

    if subtotal is None:
        return ["Invalid invoice subtotal"]

    if calculated_subtotal.quantize(Decimal("0.01")) != subtotal.quantize(Decimal("0.01")):

        errors.append(
            f"Subtotal mismatch. "
            f"Expected {calculated_subtotal}, Found {subtotal}"
        )

    return errors


# 4. Tax Validation

def validate_tax(tax):

    errors = []

    tax_value = to_decimal(tax)

    if tax_value is None:
        errors.append("Invalid tax amount")

    elif tax_value < 0:
        errors.append("Tax cannot be negative")

    return errors


# 5. Grand Total Validation

def validate_grand_total(subtotal, tax, total_amount):

    errors = []

    subtotal_value = to_decimal(subtotal)
    tax_value = to_decimal(tax)
    total_value = to_decimal(total_amount)

    if subtotal_value is None or tax_value is None or total_value is None:
        return ["Invalid grand total calculation values"]

    expected_total = subtotal_value + tax_value

    if expected_total.quantize(Decimal("0.01")) != total_value.quantize(Decimal("0.01")):

        errors.append(
            f"Grand total mismatch. "
            f"Expected {expected_total}, Found {total_value}"
        )

    return errors


# 6. Main Invoice Validation

def validate_invoice(invoice):

    errors = []

    if not isinstance(invoice, dict):

        return {
            "invoice_number": None,
            "status": "FAILED",
            "total_errors": 1,
            "errors": ["Invalid invoice data format"]
        }

    # Required fields
    errors.extend(validate_required_fields(invoice))

    # Line items
    line_items = invoice.get("line_items", [])

    item_errors, calculated_subtotal = validate_invoice_items(line_items)

    errors.extend(item_errors)

    # Subtotal
    errors.extend(
        validate_subtotal(
            calculated_subtotal,
            invoice.get("subtotal")
        )
    )

    # Tax
    errors.extend(
        validate_tax(invoice.get("tax"))
    )

    # Grand total
    errors.extend(
        validate_grand_total(
            invoice.get("subtotal"),
            invoice.get("tax"),
            invoice.get("total_amount")
        )
    )

    return {
        "invoice_number": invoice.get("invoice_number"),
        "status": "PASSED" if not errors else "FAILED",
        "total_errors": len(errors),
        "errors": errors
    }
