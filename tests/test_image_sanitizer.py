import os
import sys
from io import BytesIO
from pathlib import Path

os.environ.setdefault("PT_SALT", "test-salt-please-rotate")
os.environ.setdefault("UPLOAD_DIR", str(Path(__file__).resolve().parent / "_tmp_uploads"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

from app.services.image_sanitizer import sanitize_and_store


def _make_jpeg_with_exif() -> bytes:
    img = Image.new("RGB", (32, 32), color=(123, 200, 50))
    exif = img.getexif()
    exif[0x010F] = "EvilCorp"  # Make
    exif[0x0110] = "PhonewithGPS"  # Model
    exif[0x9003] = "2025:01:01 12:34:56"  # DateTimeOriginal

    buf = BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


def test_exif_is_stripped():
    raw = _make_jpeg_with_exif()

    src = Image.open(BytesIO(raw))
    assert dict(src.getexif()), "fixture must contain EXIF or the test is meaningless"

    out_path = sanitize_and_store(raw, "evil.jpg")
    cleaned = Image.open(out_path)

    assert dict(cleaned.getexif()) == {}, "EXIF survived sanitization"
    assert cleaned.size == (32, 32)
    assert cleaned.getpixel((0, 0)) != (0, 0, 0)
    out_path.unlink()


if __name__ == "__main__":
    test_exif_is_stripped()
    print("Image sanitizer test passed")
