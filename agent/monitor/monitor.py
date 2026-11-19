
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from agent.monitor.checksum import calculate_checksum


INCOMING_DIR = "../incoming"

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg"
}


class InvoiceMonitor(FileSystemEventHandler):

    def process_file(self, file_path):

        if not os.path.isfile(file_path):
            return

        extension = os.path.splitext(file_path)[1].lower()

        if extension not in SUPPORTED_EXTENSIONS:
            return

        # Wait until file copying is complete
        time.sleep(1)

        try:
            checksum = calculate_checksum(file_path)

            print("\nNew Invoice Detected")
            print("File:", file_path)
            print("Checksum:", checksum)

            # Next step: Check duplicate in PostgreSQL

        except Exception as e:
            print("File processing failed:", file_path)
            print("Error:", e)

    def on_created(self, event):

        if not event.is_directory:
            self.process_file(event.src_path)


def start_monitoring():

    if not os.path.isdir(INCOMING_DIR):
        raise FileNotFoundError(
            f"Incoming folder not found: {INCOMING_DIR}"
        )

    event_handler = InvoiceMonitor()

    observer = Observer()
    observer.schedule(
        event_handler,
        INCOMING_DIR,
        recursive=True
    )

    observer.start()

    print("Invoice Monitor Started")
    print("Watching:", os.path.abspath(INCOMING_DIR))

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    start_monitoring()
