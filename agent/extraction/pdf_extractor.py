
import pytesseract
import pymupdf

from PIL import Image
from io import BytesIO


def extract_pdf(file_path: str):

    doc = None

    try:
        # Open actual PDF file
        doc = pymupdf.open(file_path)

        extracted_text = []

        # Step 1: Direct PDF text extraction
        for page in doc:

            text = page.get_text()

            if text.strip():
                extracted_text.append(text)

        raw_text = "\n".join(extracted_text)

        # Step 2: OCR fallback
        if not raw_text.strip():

            extracted_text = []

            for page in doc:

                pix = page.get_pixmap(dpi=300)

                image = Image.open(
                    BytesIO(pix.tobytes("png"))
                )

                text = pytesseract.image_to_string(
                    image,
                    lang="eng"
                )

                if text.strip():
                    extracted_text.append(text)

            raw_text = "\n".join(extracted_text)

            method = "OCR"

        else:
            method = "PDF_TEXT"

        if not raw_text.strip():
            return {
                "raw_text": None,
                "extraction_method": method,
                "status": "FAILED",
                "error": "No text found even after OCR"
            }

        return {
            "raw_text": raw_text,
            "extraction_method": method,
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

    finally:
        if doc is not None:
            doc.close()
