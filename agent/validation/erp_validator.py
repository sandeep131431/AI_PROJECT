
import json
import yaml
import urllib.request
import urllib.error

from pathlib import Path
from decimal import Decimal, InvalidOperation

from agent.database.connection import get_db_connection


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ERP_BASE_URL = "http://localhost:8000"

RULES_FILE = PROJECT_ROOT / "configs" / "rules.yaml"


# --------------------------------------------------
# 1. Load Rules
# --------------------------------------------------

def load_rules():

    with open(RULES_FILE, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


# --------------------------------------------------
# 2. API Request
# --------------------------------------------------

def erp_get(endpoint):

    url = f"{ERP_BASE_URL}{endpoint}"

    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
        method="GET"
    )

    try:

        with urllib.request.urlopen(request, timeout=10) as response:

            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:

        if error.code == 404:
            return None

        raise RuntimeError(
            f"ERP API error {error.code}: {endpoint}"
        )

    except urllib.error.URLError as error:

        raise RuntimeError(
            f"Cannot connect to ERP: {error.reason}"
        )


# --------------------------------------------------
# 3. Helper Functions
# --------------------------------------------------

def get_value(data, *keys):

    if not isinstance(data, dict):
        return None

    for key in keys:

        if key in data and data[key] is not None:
            return data[key]

    return None


def unwrap(data):

    if isinstance(data, dict):

        for key in ("data", "result", "record"):

            if isinstance(data.get(key), dict):
                return data[key]

    return data


def get_line_items(po_data):

    if not isinstance(po_data, dict):
        return []

    for key in ("line_items", "items", "lines", "po_items"):

        value = po_data.get(key)

        if isinstance(value, list):
            return value

    return []


def to_decimal(value):

    if value is None:
        return None

    try:
        return Decimal(str(value).replace(",", "").strip())

    except (InvalidOperation, ValueError):
        return None


def percentage_difference(invoice_value, erp_value):

    invoice_value = to_decimal(invoice_value)
    erp_value = to_decimal(erp_value)

    if invoice_value is None or erp_value is None:
        return None

    if erp_value == 0:
        return Decimal("0") if invoice_value == 0 else Decimal("100")

    return (
        abs(invoice_value - erp_value)
        / abs(erp_value)
    ) * Decimal("100")


# --------------------------------------------------
# 4. Discrepancy Builder
# --------------------------------------------------

def add_discrepancy(
    discrepancies,
    field_name,
    invoice_value,
    erp_value,
    severity="HIGH",
    deviation=None
):

    discrepancies.append({
        "field_name": field_name,
        "invoice_value": str(invoice_value),
        "erp_value": str(erp_value),
        "deviation_pct": (
            round(float(deviation), 4)
            if deviation is not None else None
        ),
        "severity": severity
    })


# --------------------------------------------------
# 5. Vendor Validation
# --------------------------------------------------

def validate_vendor(invoice, discrepancies):

    vendor_id = invoice.get("vendor_id")

    if not vendor_id:
        add_discrepancy(
            discrepancies,
            "vendor_id",
            None,
            "Missing in invoice"
        )
        return None

    vendor = erp_get(f"/vendor/{vendor_id}")

    if not vendor:

        add_discrepancy(
            discrepancies,
            "vendor_id",
            vendor_id,
            "Vendor not found in ERP"
        )

        return None

    vendor = unwrap(vendor)

    erp_vendor_id = get_value(
        vendor,
        "vendor_id",
        "id",
        "code"
    )

    if erp_vendor_id is not None and str(erp_vendor_id) != str(vendor_id):

        add_discrepancy(
            discrepancies,
            "vendor_id",
            vendor_id,
            erp_vendor_id
        )

    return vendor


# --------------------------------------------------
# 6. SKU Validation
# --------------------------------------------------

def validate_sku(item, discrepancies):

    sku_code = get_value(
        item,
        "item_code",
        "sku_code",
        "sku"
    )

    if not sku_code:

        add_discrepancy(
            discrepancies,
            "item_code",
            None,
            "Missing in invoice"
        )

        return None

    sku = erp_get(f"/sku/{sku_code}")

    if not sku:

        add_discrepancy(
            discrepancies,
            f"{sku_code}.item_code",
            sku_code,
            "SKU not found in ERP"
        )

        return None

    return unwrap(sku)


# --------------------------------------------------
# 7. PO Validation
# --------------------------------------------------

def validate_purchase_order(invoice, rules, discrepancies):

    po_number = invoice.get("po_number")

    if not po_number:

        add_discrepancy(
            discrepancies,
            "po_number",
            None,
            "Missing in invoice"
        )

        return None

    po = erp_get(f"/po/{po_number}")

    if not po:

        add_discrepancy(
            discrepancies,
            "po_number",
            po_number,
            "Purchase Order not found in ERP"
        )

        return None

    po = unwrap(po)

    # Vendor comparison

    po_vendor = get_value(
        po,
        "vendor_id",
        "vendor_code"
    )

    invoice_vendor = invoice.get("vendor_id")

    if (
        po_vendor is not None
        and str(po_vendor) != str(invoice_vendor)
    ):

        add_discrepancy(
            discrepancies,
            "vendor_id_vs_po",
            invoice_vendor,
            po_vendor
        )

    # Currency comparison

    po_currency = get_value(
        po,
        "currency",
        "currency_code"
    )

    invoice_currency = invoice.get("currency")

    if (
        po_currency is not None
        and str(po_currency).upper() != str(invoice_currency).upper()
    ):

        add_discrepancy(
            discrepancies,
            "currency_vs_po",
            invoice_currency,
            po_currency
        )

    # Line item comparison

    invoice_items = invoice.get("line_items", [])
    po_items = get_line_items(po)

    price_tolerance = Decimal(
        str(rules["tolerances"]["price_difference_percent"])
    )

    quantity_tolerance = Decimal(
        str(rules["tolerances"]["quantity_difference_percent"])
    )

    matched_po_items = {}

    for po_item in po_items:

        code = get_value(
            po_item,
            "item_code",
            "sku_code",
            "sku"
        )

        if code is not None:
            matched_po_items[str(code)] = po_item

    for index, item in enumerate(invoice_items):

        sku_code = get_value(
            item,
            "item_code",
            "sku_code",
            "sku"
        )

        po_item = matched_po_items.get(str(sku_code))

        if not po_item:

            add_discrepancy(
                discrepancies,
                f"line_items[{index}].item_code",
                sku_code,
                "SKU not found in PO"
            )

            continue

        # Quantity comparison

        invoice_qty = get_value(item, "quantity", "qty")
        erp_qty = get_value(po_item, "quantity", "qty")

        if invoice_qty is not None and erp_qty is not None:

            difference = percentage_difference(
                invoice_qty,
                erp_qty
            )

            if difference is not None and difference > quantity_tolerance:

                add_discrepancy(
                    discrepancies,
                    f"line_items[{index}].quantity",
                    invoice_qty,
                    erp_qty,
                    deviation=difference
                )

        # Unit price comparison

        invoice_price = get_value(item, "unit_price")
        erp_price = get_value(po_item, "unit_price", "price")

        if invoice_price is not None and erp_price is not None:

            difference = percentage_difference(
                invoice_price,
                erp_price
            )

            if difference is not None and difference > price_tolerance:

                add_discrepancy(
                    discrepancies,
                    f"line_items[{index}].unit_price",
                    invoice_price,
                    erp_price,
                    severity="MEDIUM",
                    deviation=difference
                )

    return po


# --------------------------------------------------
# 8. Currency Validation
# --------------------------------------------------

def validate_currency(invoice, rules, discrepancies):

    currency = invoice.get("currency")

    if not currency:
        add_discrepancy(
            discrepancies,
            "currency",
            None,
            "Missing currency"
        )
        return

    currency = str(currency).upper()

    accepted = rules.get("accepted_currencies", [])

    if currency not in accepted:

        add_discrepancy(
            discrepancies,
            "currency",
            currency,
            "Currency not accepted",
            severity="HIGH"
        )


# --------------------------------------------------
# 9. Tax Validation
# --------------------------------------------------

def validate_tax(invoice, po, rules, discrepancies):

    if not isinstance(po, dict):
        return

    invoice_tax = invoice.get("tax")

    erp_tax = get_value(
        po,
        "tax",
        "tax_amount"
    )

    if invoice_tax is None or erp_tax is None:
        return

    difference = percentage_difference(
        invoice_tax,
        erp_tax
    )

    tolerance = Decimal(
        str(rules["tolerances"]["tax_difference_percent"])
    )

    if difference is not None and difference > tolerance:

        add_discrepancy(
            discrepancies,
            "tax",
            invoice_tax,
            erp_tax,
            severity="MEDIUM",
            deviation=difference
        )


# --------------------------------------------------
# 10. Save Discrepancies
# --------------------------------------------------

def save_discrepancies(invoice_id, discrepancies):

    conn = get_db_connection()

    try:

        with conn.cursor() as cur:

            # Remove old ERP discrepancies before revalidation

            cur.execute(
                """
                DELETE FROM audit.discrepancies
                WHERE invoice_id = %s::uuid
                """,
                (invoice_id,)
            )

            for item in discrepancies:

                cur.execute(
                    """
                    INSERT INTO audit.discrepancies
                    (
                        invoice_id,
                        field_name,
                        invoice_value,
                        erp_value,
                        deviation_pct,
                        severity
                    )
                    VALUES (%s::uuid, %s, %s, %s, %s, %s)
                    """,
                    (
                        invoice_id,
                        item["field_name"],
                        item["invoice_value"],
                        item["erp_value"],
                        item["deviation_pct"],
                        item["severity"]
                    )
                )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# --------------------------------------------------
# 11. Main ERP Validation Function
# --------------------------------------------------

def run_erp_validation(invoice_id):

    rules = load_rules()

    conn = get_db_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT extracted_raw
                FROM audit.invoice_audit
                WHERE invoice_id = %s::uuid
                """,
                (invoice_id,)
            )

            row = cur.fetchone()

            if not row:
                raise ValueError("Invoice not found")

            invoice = row[0]

            if isinstance(invoice, str):
                invoice = json.loads(invoice)

            if not isinstance(invoice, dict):
                raise ValueError("Invalid invoice data")

    finally:
        conn.close()

    discrepancies = []

    # 1. Currency

    validate_currency(
        invoice,
        rules,
        discrepancies
    )

    # 2. Vendor API

    validate_vendor(
        invoice,
        discrepancies
    )

    # 3. PO API and line item comparison

    po = validate_purchase_order(
        invoice,
        rules,
        discrepancies
    )

    # 4. SKU API

    for item in invoice.get("line_items", []):

        validate_sku(
            item,
            discrepancies
        )

    # 5. Tax comparison when ERP PO provides tax

    validate_tax(
        invoice,
        po,
        rules,
        discrepancies
    )

    # 6. Persist discrepancies

    save_discrepancies(
        invoice_id,
        discrepancies
    )

    # 7. Determine validation status

    if not discrepancies:
        status = "PASSED"

    else:
        status = "FAILED"

    result = {
        "invoice_id": str(invoice_id),
        "status": status,
        "total_discrepancies": len(discrepancies),
        "discrepancies": discrepancies
    }

    return result
