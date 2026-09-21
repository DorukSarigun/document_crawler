import io
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from ._xml import local
from .base import Block, Reader


class PptxReader(Reader):
    extension = (".pptx",)

    def parse(self, file: str | Path | bytes) -> list[Block]:
        z = zipfile.ZipFile(io.BytesIO(self.load(file)))
        slides = sorted(
            n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")
        )
        blocks: list[Block] = []
        for i, name in enumerate(slides, start=1):
            root = ET.fromstring(z.read(name))
            texts = [t.text for t in root.iter() if local(t.tag) == "t" and t.text]
            preview = " ".join(texts).strip() or f"slide {i}"
            blocks.append(Block("text", preview, order=(i,)))
        return blocks

    def children(self, data: bytes) -> list[tuple[str, bytes]]:
        z = zipfile.ZipFile(io.BytesIO(data))
        return [
            (name, z.read(name))
            for name in z.namelist()
            if "/embeddings/" in name.lower() and not name.endswith("/")
        ]
