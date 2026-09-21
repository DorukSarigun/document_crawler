from pathlib import Path

import pytest

from document_crawler import Block, Node, Processor, default_readers

DATA = Path("/home/doruk/Documents/Document_crawler/data")


class FastProcessor(Processor):
    """Corpus için: layout image byte'ını OCR etmez."""

    def _finish(self, block: Block) -> Block:
        if block.kind == "image" and isinstance(block.content, bytes):
            return Block("image", f"<image {len(block.content)} bytes>", order=block.order)
        return block


def iter_nodes(node: Node):
    yield node
    for child in node.children:
        yield from iter_nodes(child)


def all_text(node: Node) -> str:
    parts = []
    for item in iter_nodes(node):
        for block in item.blocks:
            if isinstance(block.content, str) and block.content.strip():
                parts.append(block.content.strip())
    return "\n".join(parts)


def tree_stats(node: Node) -> dict:
    nodes = list(iter_nodes(node))
    blocks = [b for n in nodes for b in n.blocks]
    texts = [b for b in blocks if b.kind == "text" and isinstance(b.content, str) and b.content.strip()]
    tables = [b for b in blocks if b.kind == "table" and isinstance(b.content, str) and b.content.strip()]
    images = [b for b in blocks if b.kind == "image"]
    return {
        "nodes": len(nodes),
        "blocks": len(blocks),
        "texts": len(texts),
        "tables": len(tables),
        "images": len(images),
        "children": sum(len(n.children) for n in nodes),
        "chars": sum(len(b.content) for b in texts + tables),
    }


@pytest.fixture(scope="session")
def processor() -> Processor:
    return Processor()


@pytest.fixture(scope="session")
def fast_processor() -> Processor:
    return FastProcessor(readers=default_readers())
