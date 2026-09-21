import io
import zipfile


def sniff_ext(data: bytes) -> str | None:
    """İlk bayttan uzantı. Yoksa None."""
    if not data:
        return None
    if data.startswith(b"%PDF"):
        return ".pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return ".gif"
    if data.startswith((b"II*\x00", b"MM\x00*")):
        return ".tiff"
    if data.startswith(b"BM"):
        return ".bmp"
    if data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return ".bin"
    if data.startswith(b"PK\x03\x04"):
        return _zip_ext(data)
    head = data[:4000]
    if b"Content-Type:" in head or head.startswith(b"From ") or b"\nFrom:" in head:
        return ".eml"
    if data[:1] in (b"{", b"["):
        return ".json"
    if _looks_text(data):
        return ".txt"
    return None


def _zip_ext(data: bytes) -> str:
    try:
        names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    except zipfile.BadZipFile:
        return ".zip"
    if any(n.startswith("word/") for n in names):
        return ".docx"
    if any(n.startswith("xl/") for n in names):
        return ".xlsx"
    if any(n.startswith("ppt/") for n in names):
        return ".pptx"
    return ".zip"


def _looks_text(data: bytes) -> bool:
    sample = data[:512]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True
