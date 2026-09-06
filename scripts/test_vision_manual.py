"""Manual test script for Module 3 (Vision & Multimodal).

Usage:
  python scripts/test_vision_manual.py
  python scripts/test_vision_manual.py --image path/to/image.png --question "What valve is shown?"
"""

import argparse
from pathlib import Path
import sys

from scripts.generate_sample_diagram import generate_test_diagram
from tools.vision_tool import analyze_image


def main():
    parser = argparse.ArgumentParser(description="Manually test Vajra Vision Model (moondream via Ollama).")
    parser.add_argument("--image", type=str, default=None, help="Path to image file (png, jpg, etc.)")
    parser.add_argument("--question", type=str, default="", help="Specific question to ask about the image.")
    args = parser.parse_args()

    # If no image provided, ensure the sample diagram exists and use it
    image_path = args.image
    if not image_path:
        sample_path = Path("data/sample_images/pid_sample_diagram.png")
        if not sample_path.exists():
            print("Generating sample P&ID schematic diagram...")
            generate_test_diagram(str(sample_path))
        image_path = str(sample_path)

    question = args.question or "What components, valves, and inspection notes are visible in this schematic?"

    print("\n" + "=" * 60)
    print("      VAJRA - MANUAL VISION MODULE TEST (M3)")
    print("=" * 60)
    print(f"Target Image : {image_path}")
    print(f"Question     : {question}")
    print("=" * 60)
    print("\nSending request to local vision model (moondream:latest via Ollama)...")
    print("Please wait a few seconds...\n")

    result = analyze_image(image_path, question)

    print("-" * 60)
    print("MODEL OUTPUT:")
    print("-" * 60)
    print(result)
    print("-" * 60 + "\n")


if __name__ == "__main__":
    main()
