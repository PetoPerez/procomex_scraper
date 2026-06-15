from PIL import Image
from io import BytesIO
from core.image_validator import validate_image_bytes


def test_validate_image_bytes_ok() -> None:
    image = Image.new("RGB", (500, 500), color=(255, 255, 255))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    valid, fmt, width, height, error = validate_image_bytes(buffer.getvalue(), "https://example.com/img.jpg")

    assert valid
    assert fmt == "JPEG"
    assert width == 500
    assert height == 500
    assert error is None


def test_validate_image_bytes_small_placeholder() -> None:
    image = Image.new("RGB", (50, 50), color=(255, 255, 255))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    valid, fmt, width, height, error = validate_image_bytes(buffer.getvalue(), "https://example.com/placeholder.jpg")

    assert not valid
    assert error is not None
