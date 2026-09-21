from email import message_from_bytes
from email.policy import default
from pathlib import Path

from .base import Block, Reader


class EmlReader(Reader):
    extension = (".eml",)

    def parse(self, file: str | Path | bytes) -> list[Block]:
        msg = message_from_bytes(self.load(file), policy=default)
        blocks: list[Block] = []
        subject = msg.get("Subject")
        if subject:
            blocks.append(Block("text", f"Subject: {subject}", order=(0,)))
        body = msg.get_body(preferencelist=("plain", "html"))
        if body is not None:
            content = body.get_content()
            if isinstance(content, str) and content.strip():
                blocks.append(Block("text", content.strip(), order=(1,)))
        return blocks

    def children(self, data: bytes) -> list[tuple[str, bytes]]:
        msg = message_from_bytes(data, policy=default)
        children: list[tuple[str, bytes]] = []
        for i, part in enumerate(msg.iter_attachments()):
            name = part.get_filename() or f"attachment-{i}"
            payload = part.get_content()
            if isinstance(payload, str):
                payload = payload.encode("utf-8", errors="replace")
            children.append((name, payload))
        if children:
            return children
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                name = part.get_filename() or "attachment"
                children.append((name, part.get_payload(decode=True) or b""))
        return children
