import io
import zipfile
from pathlib import Path

from .base import Block, Reader


class OleReader(Reader):
    extension = (".bin", ".doc", ".xls", ".ppt", ".msg")

    def parse(self, file: str | Path | bytes) -> list[Block]:
        return [Block("embed", "OLE wrapper", order=(0,))]

    def children(self, data: bytes) -> list[tuple[str, bytes]]:
        inner = self._unwrap(data)
        if inner is None:
            return []
        return [(self._child_name(inner), inner)]

    def _unwrap(self, data: bytes) -> bytes | None:
        for magic in (b"%PDF", b"PK\x03\x04", b"\x89PNG", b"\xff\xd8\xff"):
            i = data.find(magic)
            if i >= 0:
                return data[i:]
        return None

    def _child_name(self, data: bytes) -> str:
        if data.startswith(b"%PDF"):
            return "payload.pdf"
        if data.startswith(b"\xff\xd8\xff"):
            return "payload.jpg"
        if data.startswith(b"\x89PNG"):
            return "payload.png"
        if data.startswith(b"PK\x03\x04"):
            try:
                names = zipfile.ZipFile(io.BytesIO(data)).namelist()
            except zipfile.BadZipFile:
                return "payload.zip"
            if any(n.startswith("word/") for n in names):
                return "payload.docx"
            if any(n.startswith("xl/") for n in names):
                return "payload.xlsx"
            if any(n.startswith("ppt/") for n in names):
                return "payload.pptx"
            return "payload.zip"
        return "payload.bin"
