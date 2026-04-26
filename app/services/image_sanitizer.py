import secrets
from datetime import datetime
from pathlib import Path

from PIL import Image

from app.config import UPLOAD_DIR

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
FORMAT_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def sanitize_and_store(file_bytes: bytes, original_filename: str) -> Path:
    """Strip every byte of metadata by re-creating the image from raw pixels.

    EXIF, GPS, XMP, IPTC, ICC profile, and any other ancillary chunks live
    *outside* the pixel grid. Constructing a fresh Image with Image.new and
    copying the pixel data via paste guarantees only pixels survive.
    """
    from io import BytesIO

    src = Image.open(BytesIO(file_bytes))
    src.load()

    if src.format not in ALLOWED_FORMATS:
        raise ValueError(
            f"Unsupported image format: {src.format}. Allowed: {sorted(ALLOWED_FORMATS)}"
        )

    fmt = src.format
    mode = "RGBA" if fmt in {"PNG", "WEBP"} and src.mode in {"RGBA", "LA", "P"} else "RGB"

    if src.mode != mode:
        src = src.convert(mode)

    cleansed = Image.new(mode, src.size)
    cleansed.paste(src)

    extension = FORMAT_EXTENSIONS[fmt]
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    safe_name = f"{timestamp}_{secrets.token_hex(8)}{extension}"
    dest = UPLOAD_DIR / safe_name

    save_kwargs = {"format": fmt}
    if fmt == "JPEG":
        save_kwargs["quality"] = 92
        save_kwargs["optimize"] = True

    cleansed.save(dest, **save_kwargs)
    return dest
