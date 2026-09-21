from pathlib import Path

import pymupdf

from .base import Block, Reader


def reading_key(block: dict) -> tuple[int, float]:
    x0, y0, *_ = block["bbox"]
    return (round(y0 / 8), x0)


class PdfReader(Reader):
    extension = (".pdf",)

    def parse(self, file: str | Path | bytes) -> list[Block]:
        data = self.load(file)
        doc = pymupdf.open(stream=data, filetype="pdf")
        blocks: list[Block] = []
        try:
            if doc.is_encrypted or doc.needs_pass:
                return [Block("text", "encrypted pdf", order=(0,))]
            for page_no, page in enumerate(doc, start=1):
                raw = sorted(page.get_text("dict")["blocks"], key=reading_key)
                for i, block in enumerate(raw):
                    order = (page_no, i)
                    if block["type"] == 0:
                        text = " ".join(
                            span["text"]
                            for line in block["lines"]
                            for span in line["spans"]
                        ).strip()
                        if text:
                            blocks.append(Block("text", text, order=order))
                    elif block["type"] == 1:
                        blocks.append(Block("image", block.get("image") or b"", order=order))
        finally:
            doc.close()
        return blocks

    def children(self, data: bytes) -> list[tuple[str, bytes]]:
        doc = pymupdf.open(stream=data, filetype="pdf")
        try:
            if doc.is_encrypted or doc.needs_pass:
                return []
            names = doc.embfile_names() or []
            return [(name, doc.embfile_get(name)) for name in names]
        finally:
            doc.close()
