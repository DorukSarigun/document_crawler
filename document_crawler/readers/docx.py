import io
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from ._xml import R, W, WP, local
from .base import Block, Reader


class DocxReader(Reader):
    extension = (".docx",)

    def parse(self, file: str | Path | bytes) -> list[Block]:
        z = zipfile.ZipFile(io.BytesIO(self.load(file)))
        root = ET.fromstring(z.read("word/document.xml"))
        rels = ET.fromstring(z.read("word/_rels/document.xml.rels"))
        rid_to_target = {rel.attrib.get("Id"): rel.attrib.get("Target") for rel in rels}
        body = root.find(f"{W}body")
        if body is None:
            return []

        blocks: list[Block] = []
        for i, child in enumerate(list(body)):
            tag = local(child.tag)
            if tag == "p":
                text = "".join(t.text or "" for t in child.iter(f"{W}t")).strip()
                if text:
                    blocks.append(Block("text", text, order=(i,)))
                for drawing in child.iter(f"{W}drawing"):
                    rid = next(
                        (
                            el.attrib.get(f"{R}embed")
                            for el in drawing.iter()
                            if local(el.tag) == "blip"
                        ),
                        None,
                    )
                    target = rid_to_target.get(rid)
                    if not target:
                        continue
                    part = target if target.startswith("word/") else f"word/{target.lstrip('/')}"
                    if part in z.namelist():
                        blocks.append(Block("image", z.read(part), order=(i,)))
            elif tag == "tbl":
                rows = [
                    "".join(t.text or "" for t in row.iter(f"{W}t")).strip()
                    for row in child
                    if local(row.tag) == "tr"
                ]
                preview = " | ".join(r for r in rows if r) or f"{len(rows)} satır"
                blocks.append(Block("table", preview, order=(i,)))
        return blocks

    def children(self, data: bytes) -> list[tuple[str, bytes]]:
        z = zipfile.ZipFile(io.BytesIO(data))
        return [
            (name, z.read(name))
            for name in z.namelist()
            if "/embeddings/" in name.lower() and not name.endswith("/")
        ]
