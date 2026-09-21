from pathlib import Path

from .base import Block, Reader


class TextReader(Reader):
    extension = (".txt", ".csv", ".json", ".md", ".html", ".xml")

    def parse(self, file: str | Path | bytes) -> list[Block]:
        text = self.load(file).decode("utf-8", errors="replace").strip()
        return [Block("text", text, order=(0,))] if text else []

    def children(self, data: bytes) -> list[tuple[str, bytes]]:
        return []
