import json
from pathlib import Path

from document_crawler.settings import VlmSettings

from .base import Block, Node, Reader
from .docx import DocxReader
from .eml import EmlReader
from .image import ImageReader
from .ole import OleReader
from .pdf import PdfReader
from .pptx import PptxReader
from .sniff import sniff_ext
from .text import TextReader
from .vlm import HttpVlm, Vlm
from .xlsx import XlsxReader
from .zip import ZipReader

MAX_DEPTH = 8
OUTPUT_DIR = Path.cwd() / "output"
IMAGE_EXTS = {ext.lower() for ext in ImageReader.extension}


def default_readers() -> list[Reader]:
    return [
        PdfReader(),
        DocxReader(),
        XlsxReader(),
        PptxReader(),
        ImageReader(),
        TextReader(),
        EmlReader(),
        ZipReader(),
        OleReader(),
    ]


class Processor:
    """Uzantıdan reader seç, parse et, image bloklarını işle, children'da recurse."""

    def __init__(
        self,
        readers: list[Reader] | None = None,
        max_depth: int = MAX_DEPTH,
        vlm: Vlm | None = None,
        vlm_quality: float | None = None,
    ):
        self.readers = readers or default_readers()
        self.max_depth = max_depth
        self._by_ext: dict[str, Reader] = {}
        self.image_reader: ImageReader | None = None
        for reader in self.readers:
            for ext in reader.extension:
                self._by_ext[ext.lower()] = reader
            if isinstance(reader, ImageReader):
                self.image_reader = reader
        settings = VlmSettings()
        self.vlm_quality = settings.quality if vlm_quality is None else vlm_quality
        self.vlm = vlm
        if self.vlm is None and settings.api_key and settings.url:
            self.vlm = HttpVlm(settings)

    def detect(self, source: str | Path | bytes, name: str | None = None) -> Reader | None:
        filename = name
        if filename is None and isinstance(source, (str, Path)):
            filename = Path(source).name
        if filename:
            reader = self._by_ext.get(Path(filename).suffix.lower())
            if reader is not None:
                return reader
        data = source if isinstance(source, bytes) else None
        if data is None:
            return None
        for reader in self.readers:
            if reader.accepts(data):
                return reader
        return None

    def collect_files(
        self,
        root: str | Path,
        extensions: set[str] | None = None,
    ) -> list[Path]:
        root = Path(root).resolve()
        if root.is_file():
            return [root] if self._include_root(root, extensions) else []
        return sorted(
            p for p in root.rglob("*") if p.is_file() and self._include_root(p, extensions)
        )

    def _include_root(self, path: Path, extensions: set[str] | None) -> bool:
        if self.detect(path) is None and not self._vlm_handles(path, path.name):
            return False
        if extensions is None:
            return True
        return path.suffix.lower() in extensions

    def _uses_vlm(self) -> bool:
        return self.image_reader is None and self.vlm is not None

    def _vlm_handles(self, source: str | Path | bytes, name: str) -> bool:
        if not self._uses_vlm():
            return False
        if Path(name).suffix.lower() in IMAGE_EXTS:
            return True
        data = source if isinstance(source, bytes) else None
        return data is not None and sniff_ext(data) in IMAGE_EXTS

    def process(
        self,
        source: str | Path | bytes,
        name: str | None = None,
        depth: int = 0,
    ) -> Node:
        if name is None:
            name = Path(source).name if isinstance(source, (str, Path)) else "bytes"
        reader = self.detect(source, name=name)
        if reader is not None:
            kind = reader.extension[0].lstrip(".")
        else:
            kind = Path(name).suffix.lower().lstrip(".") or "unknown"
        node = Node(name=name, kind=kind)
        if depth >= self.max_depth:
            return node
        if reader is None:
            if self._vlm_handles(source, name):
                data = source if isinstance(source, bytes) else Path(source).read_bytes()
                node.blocks = [Block("text", self.vlm.read(data).strip(), order=(0,))]
            return node

        data = reader.load(source)
        if isinstance(reader, ImageReader):
            node.blocks = [self._read_image(data, kind="text", order=(0,))]
            return node
        node.blocks = [self._finish(block) for block in reader.parse(data)]
        for child_name, child_bytes in reader.children(data):
            node.children.append(self.process(child_bytes, name=child_name, depth=depth + 1))
        return node

    def write(self, node: Node, dest: str | Path | None = None) -> Path:
        dest = Path(dest) if dest else OUTPUT_DIR / f"{node.name}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(node.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return dest

    def write_txt(self, node: Node, dest: str | Path | None = None) -> Path:
        dest = Path(dest) if dest else OUTPUT_DIR / f"{node.name}.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(self._blocks_text(node), encoding="utf-8")
        return dest

    def _blocks_text(self, node: Node) -> str:
        parts: list[str] = []
        for block in node.blocks:
            if isinstance(block.content, str) and block.content.strip():
                parts.append(block.content.strip())
        for child in node.children:
            text = self._blocks_text(child)
            if text:
                parts.append(text)
        return "\n\n".join(parts)

    def _finish(self, block: Block) -> Block:
        if block.kind != "image" or not isinstance(block.content, bytes):
            return block
        return self._read_image(block.content, kind="image", order=block.order)

    def _read_image(self, image: bytes, kind: str, order: tuple | None) -> Block:
        if self.image_reader:
            text, quality = self.image_reader.ocr(image)
            if self.vlm and quality < self.vlm_quality:
                text = self.vlm.read(image)
            return Block(kind, text.strip(), order=order)
        if self.vlm:
            return Block(kind, self.vlm.read(image).strip(), order=order)
        return Block(kind, image, order=order)
