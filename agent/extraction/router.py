
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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INCOMING_FOLDER = PROJECT_ROOT / "incoming"


def route_file(file_info):

    file_path = file_info["file_path"]
    extension = Path(file_path).suffix.lower()

    # Step 1: Checksum status

    if file_info["status"] != "SUCCESS":
        return {
            **file_info,
            "raw_text": None,
            "language": None,
            "translated_text": None,
            "invoice_data": None,
            "extraction_status": "FAILED",
            "field_extraction_status": "SKIPPED",
            "database_status": "SKIPPED",
            "error": file_info.get("error", "Checksum failed")
        }

    # Step 2: Check duplicate in Neon DB

    existing_invoice_id = find_existing_checksum(
        file_info.get("checksum")
    )

    if existing_invoice_id:

        return {
            **file_info,
            "extraction_status": "SKIPPED",
            "field_extraction_status": "SKIPPED",
            "database_status": "DUPLICATE",
            "existing_invoice_id": existing_invoice_id,
            "message": "Invoice already processed"
        }

    # Step 3: File Extraction

    if extension == ".pdf":
        result = extract_pdf(file_path)

    elif extension == ".docx":
        result = extract_docx(file_path)

    elif extension in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}:
        result = extract_image(file_path)

    else:
        return {
            **file_info,
            "extraction_status": "SKIPPED",
            "field_extraction_status": "SKIPPED",
            "database_status": "SKIPPED",
            "message": "Unsupported file format"
        }

    if result["status"] != "SUCCESS":

        return {
            **file_info,
            **result,
            "extraction_status": "FAILED",
            "field_extraction_status": "SKIPPED",
            "database_status": "SKIPPED"
        }

    raw_text = result["raw_text"]

    # Step 4: Language Detection

    language_result = detect_language(raw_text)

    if language_result["status"] != "SUCCESS":

        return {
            **file_info,
            **result,
            "language": None,
            "translated_text": None,
            "invoice_data": None,
            "extraction_status": "SUCCESS",
            "language_status": "FAILED",
            "translation_status": "SKIPPED",
            "field_extraction_status": "SKIPPED",
            "database_status": "SKIPPED",
            "language_error": language_result.get("error")
        }

    language = language_result["language_code"]

    # Step 5: Translation

    translation_result = translate_to_english(
        raw_text,
        language
    )

    translated_text = translation_result.get("translated_text")

    # Step 6: Structured Field Extraction

    if translated_text:

        field_result = extract_invoice_fields(translated_text)

    else:

        field_result = {
            "invoice_data": None,
            "status": "SKIPPED",
            "error": "Translated text not available"
        }

    # Step 7: Prepare final result

    final_result = {
        **file_info,
        **result,

        "raw_text": raw_text,

        "language": language,
        "language_status": "SUCCESS",

        "translated_text": translated_text,
        "translation_status": translation_result.get("status"),
        "translation_error": translation_result.get("error"),

        "invoice_data": field_result.get("invoice_data"),
        "field_extraction_status": field_result.get("status"),
        "field_extraction_error": field_result.get("error"),

        "extraction_status": "SUCCESS"
    }

    return final_result


def run_extraction_router():

    print("\n========== INVOICE ROUTER ==========\n")

    monitored_files = process_incoming_folder(
        str(INCOMING_FOLDER)
    )

    results = []

    for file_info in monitored_files:

        print(f"\nProcessing: {file_info['file_name']}")

        try:

            result = route_file(file_info)

            # Step 8: Save invoice into Neon DB

            if result.get("field_extraction_status") == "SUCCESS":

                database_result = save_invoice(result)

                result["database_status"] = database_result.get("status")

                result["database_message"] = database_result.get("message")

                result["invoice_id"] = database_result.get("invoice_id")

            results.append(result)

        except Exception as error:

            result = {
                **file_info,
                "extraction_status": "FAILED",
                "field_extraction_status": "FAILED",
                "database_status": "FAILED",
                "error": str(error)
            }

            results.append(result)

        # Step 9: Print results

        print("Checksum:", result.get("checksum"))
        print("Extraction:", result.get("extraction_status"))
        print("Language:", result.get("language"))
        print("Translation:", result.get("translation_status"))
        print("Field Extraction:", result.get("field_extraction_status"))
        print("Database:", result.get("database_status"))

        if result.get("invoice_id"):
            print("Invoice ID:", result["invoice_id"])

        if result.get("invoice_data"):

            print("\nStructured Invoice Data:")

            for key, value in result["invoice_data"].items():
                print(f"{key}: {value}")

        if result.get("error"):
            print("Error:", result["error"])

        if result.get("translation_error"):
            print("Translation Error:", result["translation_error"])

        if result.get("field_extraction_error"):
            print("Field Extraction Error:", result["field_extraction_error"])

        if result.get("database_message"):
            print("Database Message:", result["database_message"])

        print("-" * 60)

    return results


if __name__ == "__main__":

    results = run_extraction_router()

    successful = sum(
        1 for item in results
        if item.get("extraction_status") == "SUCCESS"
    )

    failed = sum(
        1 for item in results
        if item.get("extraction_status") == "FAILED"
    )

    field_successful = sum(
        1 for item in results
        if item.get("field_extraction_status") == "SUCCESS"
    )

    database_successful = sum(
        1 for item in results
        if item.get("database_status") == "SUCCESS"
    )

    duplicates = sum(
        1 for item in results
        if item.get("database_status") == "DUPLICATE"
    )

    print("\n========== SUMMARY ==========")

    print("Total Files:", len(results))
    print("Successful Extraction:", successful)
    print("Failed Extraction:", failed)
    print("Successful Field Extraction:", field_successful)
    print("Database Saved:", database_successful)
    print("Duplicate Files:", duplicates)
