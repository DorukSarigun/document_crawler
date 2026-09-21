from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .sniff import sniff_ext


@dataclass
class Block:
    kind: str
    content: Any
    order: tuple | None = None

    def to_dict(self) -> dict[str, Any]:
        content = self.content
        if isinstance(content, bytes):
            content = f"<{len(content)} bytes>"
        return {"kind": self.kind, "content": content, "order": self.order}


@dataclass
class Node:
    name: str
    kind: str
    blocks: list[Block] = field(default_factory=list)
    children: list["Node"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "blocks": [b.to_dict() for b in self.blocks],
            "children": [c.to_dict() for c in self.children],
        }

    def print_tree(self, indent: int = 0) -> None:
        pad = "    " * indent
        print(f"{pad}{self.name}  [{self.kind}]")
        for block in self.blocks[:16]:
            preview = block.content if isinstance(block.content, str) else type(block.content).__name__
            print(f"{pad}  · {block.kind:5} {str(preview)[:90]}")
        if len(self.blocks) > 16:
            print(f"{pad}  · … +{len(self.blocks) - 16}")
        for child in self.children:
            child.print_tree(indent + 1)


class Reader(ABC):
    extension: tuple[str, ...] = ()

    def load(self, file: str | Path | bytes) -> bytes:
        if isinstance(file, bytes):
            return file
        return Path(file).read_bytes()

    def accepts(self, data: bytes) -> bool:
        ext = sniff_ext(data)
        return ext is not None and ext in {e.lower() for e in self.extension}

    @abstractmethod
    def parse(self, file: str | Path | bytes) -> list[Block]:
        """Bu katmanın içeriği. Recursion yok."""
        pass
    
    @abstractmethod
    def children(self, data: bytes) -> list[tuple[str, bytes]]:
        """Gömülü dosyalar. Layout image yok."""
        pass