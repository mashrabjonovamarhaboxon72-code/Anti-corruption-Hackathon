import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image

from app.config import UPLOAD_DIR

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
FORMAT_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


@dataclass
class SanitizedImage:
    path: Path
    sha256_hash: str
    size_bytes: int
    format: str


def sanitize_and_store(file_bytes: bytes, original_filename: str) -> SanitizedImage:
    """Strip every byte of metadata by re-creating the image from raw pixels.

    EXIF, GPS, XMP, IPTC, ICC profile, and any other ancillary chunks live
    *outside* the pixel grid. Constructing a fresh Image with Image.new and
    copying the pixel data via paste guarantees only pixels survive.

    Returns a SanitizedImage carrying the on-disk path, the SHA-256 of the
    bytes that were actually written, and the size. The hash is computed
    on the cleansed payload (not the original upload) so it can later be
    used as an integrity anchor: if anyone tampers with the file on disk,
    re-hashing yields a different digest and integrity verification fails.
    """
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

    save_kwargs = {"format": fmt}
    if fmt == "JPEG":
        save_kwargs["quality"] = 92
        save_kwargs["optimize"] = True

    # Render to bytes first so the on-disk file and the digest are computed
    # from the exact same payload. Writing-then-reading would race against
    # filesystem corruption.
    buf = BytesIO()
    cleansed.save(buf, **save_kwargs)
    payload = buf.getvalue()
    sha256_hash = hashlib.sha256(payload).hexdigest()

    extension = FORMAT_EXTENSIONS[fmt]
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    safe_name = f"{timestamp}_{secrets.token_hex(8)}{extension}"
    dest = UPLOAD_DIR / safe_name

    dest.write_bytes(payload)

    return SanitizedImage(
        path=dest,
        sha256_hash=sha256_hash,
        size_bytes=len(payload),
        format=fmt,
    )


def hash_file(path: Path) -> str | None:
    """SHA-256 of a file on disk. Returns None if the file is missing."""
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
