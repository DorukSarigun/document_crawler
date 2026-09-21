import io
import zipfile
from pathlib import Path

from .base import Block, Reader


class ZipReader(Reader):
    extension = (".zip",)

    def parse(self, file: str | Path | bytes) -> list[Block]:
        names = zipfile.ZipFile(io.BytesIO(self.load(file))).namelist()
        members = [n for n in names if not n.endswith("/")]
        return [Block("embed", f"zip {len(members)} entry", order=(0,))]

    def children(self, data: bytes) -> list[tuple[str, bytes]]:
        z = zipfile.ZipFile(io.BytesIO(data))
        return [(n, z.read(n)) for n in z.namelist() if not n.endswith("/")]
