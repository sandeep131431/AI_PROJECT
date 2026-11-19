import pytesseract

from PIL import Image


def extract_image(file_path: str):

    try:

        image = Image.open(file_path)

        # OCR extraction
        raw_text = pytesseract.image_to_string(
            image,
            lang="eng"
        )

        if not raw_text.strip():
            return {
                "raw_text": None,
                "extraction_method": "OCR",
                "status": "FAILED",
                "error": "No text found in image"
            }

        return {
            "raw_text": raw_text,
            "extraction_method": "OCR",
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