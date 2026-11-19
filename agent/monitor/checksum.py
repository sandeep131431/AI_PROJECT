
import hashlib
import pathlib
import os
from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".bmp"
}


def calculate_checksum(file_path: str) -> str:

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:

        while True:
            chunk = file.read(4096)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


def process_incoming_folder(folder_path: str):

    if not os.path.isdir(folder_path):
        raise FileNotFoundError(
            f"Incoming folder not found: {folder_path}"
        )

    results = []

    for filename in os.listdir(folder_path):

        file_path = os.path.join(folder_path, filename)

        # Ignore directories
        if not os.path.isfile(file_path):
            continue

        extension = os.path.splitext(filename)[1].lower()

        # Accept only supported invoice formats
        if extension not in SUPPORTED_EXTENSIONS:
            continue

        try:
            checksum = calculate_checksum(file_path)

            results.append({
                "file_name": filename,
                "file_path": file_path,
                "file_type": extension,
                "checksum": checksum,
                "status": "SUCCESS"
            })

            print(f"File: {filename}")
            print(f"Type: {extension}")
            print(f"Checksum: {checksum}")
            print("-" * 50)

        except Exception as error:

            results.append({
                "file_name": filename,
                "file_path": file_path,
                "file_type": extension,
                "checksum": None,
                "status": "FAILED",
                "error": str(error)
            })

            print(f"Failed: {filename} - {error}")

    return results


if __name__ == "__main__":


    PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

    # Project root ke andar incoming folder
    incoming_folder = PROJECT_ROOT / "incoming"

    results = process_incoming_folder(incoming_folder)

    successful = sum(
        1 for item in results
        if item["status"] == "SUCCESS"
    )

    failed = sum(
        1 for item in results
        if item["status"] == "FAILED"
    )

    print("\n========== SUMMARY ==========")
    print("Total Supported Files:", len(results))
    print("Successful:", successful)
    print("Failed:", failed)
