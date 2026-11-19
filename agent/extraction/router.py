
from pathlib import Path

from agent.monitor.checksum import process_incoming_folder

from agent.extraction.pdf_extractor import extract_pdf
from agent.extraction.docx_extractor import extract_docx
from agent.extraction.ocr_extractor import extract_image
from agent.extraction.field_extractor import extract_invoice_fields

from agent.translation.language_detector import detect_language
from agent.translation.translator import translate_to_english

from agent.database.save_invoice import (
    find_existing_checksum,
    save_invoice
)

from agent.validation.db_validator import run_validation
from agent.validation.erp_validator import run_erp_validation


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INCOMING_FOLDER = PROJECT_ROOT / "incoming"


# --------------------------------------------------
# 1. File Extraction Router
# --------------------------------------------------

def route_file(file_info):

    file_path = file_info["file_path"]
    extension = Path(file_path).suffix.lower()

    # Check checksum status

    if file_info.get("status") != "SUCCESS":

        return {
            **file_info,
            "extraction_status": "FAILED",
            "field_extraction_status": "SKIPPED",
            "database_status": "SKIPPED",
            "validation_status": "SKIPPED",
            "erp_validation_status": "SKIPPED",
            "error": file_info.get("error", "Checksum failed")
        }

    # Check existing invoice

    existing_invoice_id = find_existing_checksum(
        file_info.get("checksum")
    )

    if existing_invoice_id:

        return {
            **file_info,
            "extraction_status": "SKIPPED",
            "field_extraction_status": "SKIPPED",
            "database_status": "DUPLICATE",
            "invoice_id": existing_invoice_id,
            "message": "Invoice already exists"
        }

    # Extract document

    if extension == ".pdf":
        extraction_result = extract_pdf(file_path)

    elif extension == ".docx":
        extraction_result = extract_docx(file_path)

    elif extension in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}:
        extraction_result = extract_image(file_path)

    else:
        return {
            **file_info,
            "extraction_status": "SKIPPED",
            "field_extraction_status": "SKIPPED",
            "database_status": "SKIPPED",
            "validation_status": "SKIPPED",
            "erp_validation_status": "SKIPPED",
            "message": "Unsupported file format"
        }

    if extraction_result.get("status") != "SUCCESS":

        return {
            **file_info,
            "extraction_status": "FAILED",
            "field_extraction_status": "SKIPPED",
            "database_status": "SKIPPED",
            "validation_status": "SKIPPED",
            "erp_validation_status": "SKIPPED",
            "error": extraction_result.get("error")
        }

    raw_text = extraction_result["raw_text"]

    # Language detection

    language_result = detect_language(raw_text)

    if language_result.get("status") != "SUCCESS":

        return {
            **file_info,
            "extraction_status": "SUCCESS",
            "field_extraction_status": "SKIPPED",
            "database_status": "SKIPPED",
            "validation_status": "SKIPPED",
            "erp_validation_status": "SKIPPED",
            "language_error": language_result.get("error")
        }

    language = language_result["language_code"]

    # Translation

    translation_result = translate_to_english(
        raw_text,
        language
    )

    translated_text = translation_result.get("translated_text")

    if (
        translation_result.get("status") != "SUCCESS"
        or not translated_text
    ):

        return {
            **file_info,
            "extraction_status": "SUCCESS",
            "language": language,
            "translation_status": "FAILED",
            "field_extraction_status": "SKIPPED",
            "database_status": "SKIPPED",
            "validation_status": "SKIPPED",
            "erp_validation_status": "SKIPPED",
            "translation_error": translation_result.get("error")
        }

    # Field extraction

    field_result = extract_invoice_fields(translated_text)

    return {
        **file_info,

        "raw_text": raw_text,

        "language": language,
        "language_status": "SUCCESS",

        "translated_text": translated_text,
        "translation_status": "SUCCESS",

        "invoice_data": field_result.get("invoice_data"),
        "field_extraction_status": field_result.get("status"),
        "field_extraction_error": field_result.get("error"),

        "extraction_status": "SUCCESS"
    }


# --------------------------------------------------
# 2. Internal + ERP Validation
# --------------------------------------------------

def validate_invoice_pipeline(invoice_id):

    result = {}

    # Internal validation

    try:

        internal_result = run_validation(invoice_id)

        result["validation_status"] = internal_result.get("status")
        result["validation_errors"] = internal_result.get("errors", [])
        result["total_validation_errors"] = internal_result.get(
            "total_errors", 0
        )

    except Exception as error:

        result["validation_status"] = "ERROR"
        result["validation_error"] = str(error)

        result["erp_validation_status"] = "SKIPPED"

        return result

    # ERP validation

    if result["validation_status"] != "PASSED":

        result["erp_validation_status"] = "SKIPPED"
        result["erp_validation_message"] = (
            "ERP validation skipped because internal validation failed"
        )

        return result

    try:

        erp_result = run_erp_validation(invoice_id)

        result["erp_validation_status"] = erp_result.get("status")
        result["total_discrepancies"] = erp_result.get(
            "total_discrepancies", 0
        )
        result["erp_discrepancies"] = erp_result.get(
            "discrepancies", []
        )

    except Exception as error:

        result["erp_validation_status"] = "ERROR"
        result["erp_validation_error"] = str(error)

    return result


# --------------------------------------------------
# 3. Main Router
# --------------------------------------------------

def run_extraction_router():

    print("\n========== INVOICE ROUTER ==========\n")

    monitored_files = process_incoming_folder(
        str(INCOMING_FOLDER)
    )

    results = []

    for file_info in monitored_files:

        print("\nProcessing:", file_info.get("file_name"))

        try:

            result = route_file(file_info)

            # Save new invoice

            if result.get("field_extraction_status") == "SUCCESS":

                database_result = save_invoice(result)

                result["database_status"] = database_result.get("status")
                result["database_message"] = database_result.get("message")
                result["invoice_id"] = database_result.get("invoice_id")

            # Validate both new and existing saved invoices

            if (
                result.get("database_status") in {"SUCCESS", "DUPLICATE"}
                and result.get("invoice_id")
            ):

                validation_result = validate_invoice_pipeline(
                    result["invoice_id"]
                )

                result.update(validation_result)

            else:

                result.setdefault("validation_status", "SKIPPED")
                result.setdefault("erp_validation_status", "SKIPPED")

            results.append(result)

        except Exception as error:

            result = {
                **file_info,
                "extraction_status": "FAILED",
                "field_extraction_status": "FAILED",
                "database_status": "FAILED",
                "validation_status": "SKIPPED",
                "erp_validation_status": "SKIPPED",
                "error": str(error)
            }

            results.append(result)

        # Print individual result

        print("\n---------- RESULT ----------")

        print("Checksum:", result.get("checksum"))
        print("Extraction:", result.get("extraction_status"))
        print("Language:", result.get("language"))
        print("Translation:", result.get("translation_status"))
        print("Field Extraction:", result.get("field_extraction_status"))
        print("Database:", result.get("database_status"))
        print("Invoice ID:", result.get("invoice_id"))

        print("Internal Validation:", result.get("validation_status"))
        print("ERP Validation:", result.get("erp_validation_status"))

        print(
            "Total Discrepancies:",
            result.get("total_discrepancies", 0)
        )

        if result.get("validation_errors"):

            print("\nInternal Validation Errors:")

            for error in result["validation_errors"]:
                print("-", error)

        if result.get("erp_discrepancies"):

            print("\nERP Discrepancies:")

            for discrepancy in result["erp_discrepancies"]:
                print("-", discrepancy)

        if result.get("error"):
            print("Error:", result["error"])

        if result.get("erp_validation_error"):
            print("ERP Error:", result["erp_validation_error"])

        if result.get("database_message"):
            print("Database Message:", result["database_message"])

        print("-" * 60)

    return results


# --------------------------------------------------
# 4. Summary
# --------------------------------------------------

if __name__ == "__main__":

    results = run_extraction_router()

    print("\n========== SUMMARY ==========")

    print("Total Files:", len(results))

    print(
        "Successful Extraction:",
        sum(1 for r in results if r.get("extraction_status") == "SUCCESS")
    )

    print(
        "Failed Extraction:",
        sum(1 for r in results if r.get("extraction_status") == "FAILED")
    )

    print(
        "Database Saved:",
        sum(1 for r in results if r.get("database_status") == "SUCCESS")
    )

    print(
        "Duplicate Files:",
        sum(1 for r in results if r.get("database_status") == "DUPLICATE")
    )

    print(
        "Internal Validation Passed:",
        sum(1 for r in results if r.get("validation_status") == "PASSED")
    )

    print(
        "Internal Validation Failed:",
        sum(1 for r in results if r.get("validation_status") == "FAILED")
    )

    print(
        "ERP Validation Passed:",
        sum(1 for r in results if r.get("erp_validation_status") == "PASSED")
    )

    print(
        "ERP Validation Failed:",
        sum(1 for r in results if r.get("erp_validation_status") == "FAILED")
    )

    print(
        "ERP Validation Errors:",
        sum(1 for r in results if r.get("erp_validation_status") == "ERROR")
    )

    print("\n========== PROCESS COMPLETED ==========\n")
