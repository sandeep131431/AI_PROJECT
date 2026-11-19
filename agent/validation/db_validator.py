
from agent.database.connection import get_db_connection
from agent.validation.validator import validate_invoice


def run_validation(invoice_id):

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            # Step 1: Fetch invoice from Neon DB

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
                raise ValueError("Invoice not found in database")

            invoice_data = row[0]

            if not isinstance(invoice_data, dict):
                raise ValueError("Invalid invoice JSON data in database")

            # Step 2: Run internal validation

            validation_result = validate_invoice(invoice_data)

            status = validation_result["status"]

            # Step 3: Update validation status in database

            cur.execute(
                """
                UPDATE audit.invoice_audit
                SET validation_status = %s
                WHERE invoice_id = %s::uuid
                """,
                (status, invoice_id)
            )

        conn.commit()

        return validation_result

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
