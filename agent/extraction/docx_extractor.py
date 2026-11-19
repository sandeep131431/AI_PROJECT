from docx import Document


def extract_docx(file_path: str):

    try:
        doc = Document(file_path)

        extracted_text = []

        # Step 1: Extract paragraphs
        for paragraph in doc.paragraphs:

            text = paragraph.text.strip()

            if text:
                extracted_text.append(text)

        # Step 2: Extract tables
        for table in doc.tables:

            for row in table.rows:

                row_data = [
                    cell.text.strip()
                    for cell in row.cells
                ]

                extracted_text.append(
                    " | ".join(row_data)
                )

        raw_text = "\n".join(extracted_text)

        if not raw_text.strip():
            return {
                "raw_text": None,
                "extraction_method": "DOCX_TEXT",
                "status": "FAILED",
                "error": "No text found in DOCX"
            }

        return {
            "raw_text": raw_text,
            "extraction_method": "DOCX_TEXT",
            "status": "SUCCESS",
            "error": None
        }

    except Exception as error:

        return {
            "raw_text": None,
            "extraction_method": None,
            "status": "FAILED",
            "error": str(error)
        }