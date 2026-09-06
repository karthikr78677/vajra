"""
Manual OCR Test — Vajra
Drop any PDF or image file into the data/ folder and test it interactively.
Run: python -m tests.test_ocr_manual
"""

import sys
import logging
import os
import time

logging.basicConfig(level=logging.WARNING)  # Suppress INFO logs for clean output

def test_file(file_path: str):
    """Run the full OCR pipeline on a real user-provided file."""
    from tools.vision_tool import extract_text, get_document_info

    path = file_path.strip().strip('"')  # Remove quotes if user drag-dropped path

    if not os.path.exists(path):
        print(f"\n[ERROR] File not found: {path}")
        print("Tip: Make sure the path is correct. You can drag-and-drop a file into the terminal to paste its path.")
        return

    ext = os.path.splitext(path)[1].lower()
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"\nFile    : {os.path.basename(path)}")
    print(f"Type    : {ext.upper()}")
    print(f"Size    : {size_mb:.2f} MB")

    # Show metadata for PDFs
    if ext == ".pdf":
        print("\n--- PDF Metadata ---")
        print(get_document_info(path))

    print("\n--- Extracting Text (this may take a moment for large files) ---")
    start = time.time()
    result = extract_text(path, lang="eng")
    elapsed = time.time() - start

    # Display up to 2000 chars
    MAX_DISPLAY = 2000
    if len(result) > MAX_DISPLAY:
        display = result[:MAX_DISPLAY] + f"\n\n... [{len(result) - MAX_DISPLAY} more characters truncated] ..."
    else:
        display = result

    print(display)
    print(f"\n--- Done in {elapsed:.2f}s | Total characters extracted: {len(result)} ---")


if __name__ == "__main__":
    print("=" * 55)
    print("  Vajra OCR Manual File Test")
    print("=" * 55)
    print("Supported: PDF, JPG, JPEG, PNG, TIF, TIFF, BMP")
    print("Tip: You can DRAG and DROP a file into this terminal window to paste its path!")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            path = input("Enter file path (or drag-and-drop): ").strip()
            if path.lower() == "exit":
                print("Goodbye!")
                break
            if path:
                test_file(path)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break
