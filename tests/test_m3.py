"""Unit tests for Module 3 (Vision & Multimodal)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image
import pytest

from tools.vision_tool import analyze_image as tool_analyze_image
from vision.analyzer import (
    PROMPT_PRESETS,
    analyze_image,
    build_vision_prompt,
    encode_image_to_base64,
    validate_and_load_image,
)
from vision.vision_engine import VisionEngine


@pytest.fixture
def sample_image(tmp_path: Path) -> str:
    """Create a temporary valid PNG image."""
    img_path = tmp_path / "test_diagram.png"
    img = Image.new("RGB", (200, 200), color=(100, 150, 200))
    img.save(str(img_path))
    return str(img_path)


def test_validate_and_load_image_success(sample_image: str):
    img = validate_and_load_image(sample_image)
    assert isinstance(img, Image.Image)
    assert img.size == (200, 200)


def test_validate_and_load_image_missing_file(tmp_path: Path):
    missing_path = str(tmp_path / "nonexistent.png")
    with pytest.raises(FileNotFoundError):
        validate_and_load_image(missing_path)


def test_validate_and_load_image_unsupported_format(tmp_path: Path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("not an image")
    with pytest.raises(ValueError, match="Unsupported image format"):
        validate_and_load_image(str(txt_file))


def test_encode_image_to_base64_and_resizing(tmp_path: Path):
    # Create a large 1500x1200 image
    large_img_path = tmp_path / "large_image.png"
    img = Image.new("RGB", (1500, 1200), color=(50, 50, 50))
    img.save(str(large_img_path))

    encoded = encode_image_to_base64(str(large_img_path), max_dimension=800)
    assert isinstance(encoded, str)
    assert len(encoded) > 0


def test_build_vision_prompt():
    # Test preset prompts
    diagram_prompt = build_vision_prompt(task_preset="diagram")
    assert "P&ID schematic" in diagram_prompt

    inspection_prompt = build_vision_prompt(task_preset="inspection")
    assert "equipment photo" in inspection_prompt

    # Test custom question overrides default preset
    custom = build_vision_prompt(prompt="What is the valve status?")
    assert "What is the valve status?" in custom


def test_analyze_image_missing_file_returns_error():
    result = analyze_image("invalid/path/to/diagram.png")
    assert result.startswith("Error loading image:")


def test_analyze_image_mocked_ollama(sample_image: str):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "The diagram displays Valve V-101 in open status."}
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        result = analyze_image(sample_image, prompt="What valve is visible?")
        assert result == "The diagram displays Valve V-101 in open status."
        
        # Verify Ollama request payload
        assert mock_post.called
        _, kwargs = mock_post.call_args
        payload = kwargs.get("json", {})
        assert payload["model"] == "moondream:latest"
        assert "What valve is visible?" in payload["prompt"]
        assert len(payload["images"]) == 1


def test_vision_engine_class_describe_image(sample_image: str):
    engine = VisionEngine()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "Pump P-301 operational."}
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.Client.post", return_value=mock_resp):
        description = engine.describe_image(sample_image)
        assert description == "Pump P-301 operational."


def test_tools_vision_tool_analyze_image_integration(sample_image: str):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "Pressure transmitter PT-202 at 12.5 bar."}
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.Client.post", return_value=mock_resp):
        res = tool_analyze_image(sample_image, question="Check pressure transmitter")
        assert res == "Pressure transmitter PT-202 at 12.5 bar."
