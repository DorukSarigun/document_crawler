import io
from pathlib import Path

import pytesseract
from PIL import Image

from .base import Block, Reader


class ImageReader(Reader):
    extension = (".jpg", ".jpeg", ".png", ".tiff", ".tif", ".gif", ".bmp", ".webp")

    def parse(self, file: str | Path | bytes) -> list[Block]:
        text, _quality = self.ocr(self.load(file))
        return [Block("text", text, order=(0,))]

    def ocr(self, data: bytes) -> tuple[str, float]:
        """Metin ve Tesseract ortalama güveni (0-100). Kelime yoksa kalite 0."""
        try:
            raw = pytesseract.image_to_data(
                Image.open(io.BytesIO(data)),
                output_type=pytesseract.Output.DICT,
            )
        except (OSError, pytesseract.TesseractError):
            return "", 0.0
        words: list[str] = []
        scores: list[float] = []
        for word, conf in zip(raw.get("text", []), raw.get("conf", [])):
            try:
                score = float(conf)
            except (TypeError, ValueError):
                continue
            if score < 0:
                continue
            scores.append(score)
            if isinstance(word, str) and word.strip():
                words.append(word.strip())
        quality = sum(scores) / len(scores) if scores else 0.0
        return " ".join(words), quality

    def children(self, data: bytes) -> list[tuple[str, bytes]]:
        return []
