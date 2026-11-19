
import uuid
from pathlib import Path

from psycopg.types.json import Jsonb

from agent.database.connection import get_db_connection


def find_existing_checksum(checksum):

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT invoice_id
                FROM audit.invoice_audit
                WHERE file_checksum = %s
                LIMIT 1
                """,
                (checksum,)
            )

            row = cur.fetchone()

            return str(row[0]) if row else None

    finally:
        conn.close()


def save_invoice(result):

    invoice_data = result.get("invoice_data")
    checksum = result.get("checksum")

    if not invoice_data:
        return {
            "status": "FAILED",
            "message": "Invoice data not available"
        }

    if not checksum:
        return {
            "status": "FAILED",
            "message": "Checksum not available"
        }

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            # Duplicate check again before insertion

            cur.execute(
                """
                SELECT invoice_id
                FROM audit.invoice_audit
                WHERE file_checksum = %s
                LIMIT 1
                """,
                (checksum,)
            )

            existing = cur.fetchone()

            if existing:
                return {
                    "status": "DUPLICATE",
                    "invoice_id": str(existing[0]),
                    "message": "Invoice already exists"
                }

            invoice_id = uuid.uuid4()

            file_path = result.get("file_path")

            extension = Path(file_path).suffix.lower()

            extraction_method = extension.replace(".", "").upper()

            # Insert invoice header

            cur.execute(
                """
                INSERT INTO audit.invoice_audit (
                    invoice_id,
                    file_path,
                    file_checksum,
                    extraction_method,
                    raw_extracted_text,
                    translated_text,
                    source_language,
                    translation_confidence,
                    invoice_number,
                    vendor_name,
                    po_number,
                    invoice_date,
                    currency,
                    total_amount,
                    validation_status,
                    recommendation,
                    extracted_raw,
                    thread_id
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    invoice_id,
                    file_path,
                    checksum,
                    extraction_method,
                    result.get("raw_text"),
                    result.get("translated_text"),
                    result.get("language"),
                    result.get("translation_confidence"),
                    invoice_data.get("invoice_number"),
                    invoice_data.get("vendor_name"),
                    invoice_data.get("po_number"),
                    invoice_data.get("invoice_date"),
                    invoice_data.get("currency"),
                    invoice_data.get("total_amount"),
                    "PENDING",
                    "PENDING",
                    Jsonb(invoice_data),
                    None
                )
            )

            # Insert invoice line items

            for line_number, item in enumerate(
                invoice_data.get("line_items", []), start=1
            ):

                cur.execute(
                    """
                    INSERT INTO audit.invoice_line_items (
                        invoice_id,
                        line_number,
                        item_code,
                        description,
                        quantity,
                        unit_price,
                        line_total
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        invoice_id,
                        line_number,
                        item.get("item_code"),
                        item.get("description"),
                        item.get("quantity"),
                        item.get("unit_price"),
                        item.get("line_total")
                    )
                )

        conn.commit()

        return {
            "status": "SUCCESS",
            "invoice_id": str(invoice_id),
            "message": "Invoice saved successfully"
        }

    except Exception as error:

        conn.rollback()

        return {
            "status": "FAILED",
            "message": str(error)
        }

    finally:
        conn.close()
