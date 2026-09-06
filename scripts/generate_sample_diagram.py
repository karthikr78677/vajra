"""Generate synthetic industrial engineering diagrams and inspection photos for testing."""

from pathlib import Path
from PIL import Image, ImageDraw


def generate_test_diagram(output_path: str) -> str:
    """Create a synthetic P&ID / engineering schematic with labeled components."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # 800x600 schematic with industrial diagram style
    img = Image.new("RGB", (800, 600), color=(245, 247, 250))
    draw = ImageDraw.Draw(img)

    # Draw title block
    draw.rectangle([20, 20, 780, 70], outline=(40, 60, 90), width=2)
    draw.text((35, 35), "VAJRA INDUSTRIAL REFINERY - P&ID SCHEMATIC (UNIT-04)", fill=(20, 30, 50))

    # Draw pipeline
    draw.line([(50, 250), (750, 250)], fill=(30, 100, 200), width=6)
    draw.text((70, 225), "INLET LINE: DN-150 / 16 BAR", fill=(30, 100, 200))

    # Draw Valve-101 (butterfly/gate valve symbol)
    draw.polygon([(250, 210), (350, 290), (350, 210), (250, 290)], fill=(200, 50, 50), outline=(0, 0, 0))
    draw.line([(300, 210), (300, 170)], fill=(0, 0, 0), width=3)
    draw.ellipse([285, 155, 315, 170], fill=(100, 100, 100), outline=(0, 0, 0))
    draw.text((260, 305), "GATE VALVE: V-101 (STATUS: OPEN)", fill=(180, 20, 20))

    # Draw Pressure Transmitter PT-202
    draw.line([(500, 250), (500, 180)], fill=(30, 100, 200), width=3)
    draw.ellipse([460, 100, 540, 180], fill=(255, 255, 255), outline=(30, 100, 200), width=3)
    draw.line([(460, 140), (540, 140)], fill=(30, 100, 200), width=2)
    draw.text((485, 115), "PT", fill=(30, 100, 200))
    draw.text((475, 150), "202", fill=(30, 100, 200))
    draw.text((450, 80), "SETPOINT: 12.5 BAR", fill=(30, 100, 200))

    # Draw inspection alert box
    draw.rectangle([450, 420, 750, 550], fill=(255, 245, 230), outline=(220, 120, 30), width=2)
    draw.text((465, 435), "INSPECTION LOG:", fill=(160, 80, 0))
    draw.text((465, 465), "- Flange seal checked on 2026-08-15", fill=(60, 60, 60))
    draw.text((465, 490), "- Surface corrosion observed on bypass bend", fill=(180, 40, 40))
    draw.text((465, 515), "- Action: Replace gasket at next shutdown", fill=(60, 60, 60))

    img.save(str(path))
    return str(path)


if __name__ == "__main__":
    out = Path("data/sample_images/pid_sample_diagram.png")
    generate_test_diagram(str(out))
    print(f"Generated test diagram at {out.resolve()}")
