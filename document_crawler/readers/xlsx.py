import io
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from ._xml import R, SS
from .base import Block, Reader


class XlsxReader(Reader):
    extension = (".xlsx",)

    def parse(self, file: str | Path | bytes) -> list[Block]:
        z = zipfile.ZipFile(io.BytesIO(self.load(file)))
        strings = self._shared_strings(z)
        blocks: list[Block] = []
        for i, (name, path) in enumerate(self._sheets(z)):
            if path not in z.namelist():
                continue
            rows = self._rows(z.read(path), strings)
            preview = f"{name}: {len(rows)} satır"
            if rows:
                preview += " — " + " | ".join(rows[0][:8])
            blocks.append(Block("table", preview, order=(i,)))
        return blocks

    def children(self, data: bytes) -> list[tuple[str, bytes]]:
        z = zipfile.ZipFile(io.BytesIO(data))
        return [
            (name, z.read(name))
            for name in z.namelist()
            if "/embeddings/" in name.lower() and not name.endswith("/")
        ]

    def _shared_strings(self, z: zipfile.ZipFile) -> list[str]:
        if "xl/sharedStrings.xml" not in z.namelist():
            return []
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        return [
            "".join(t.text or "" for t in si.iter(f"{SS}t"))
            for si in root.findall(f"{SS}si")
        ]

    def _sheets(self, z: zipfile.ZipFile) -> list[tuple[str, str]]:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid_to_target = {rel.attrib.get("Id"): rel.attrib.get("Target") for rel in rels}
        out = []
        for sheet in wb.findall(f"{SS}sheets/{SS}sheet"):
            rid = sheet.attrib.get(f"{R}id")
            target = (rid_to_target.get(rid, "") or "").lstrip("/")
            path = target if target.startswith("xl/") else f"xl/{target}"
            out.append((sheet.attrib.get("name", "Sheet"), path))
        return out

    def _rows(self, xml: bytes, strings: list[str]) -> list[list[str]]:
        root = ET.fromstring(xml)
        rows = []
        for row in root.findall(f"{SS}sheetData/{SS}row"):
            values = []
            for cell in row.findall(f"{SS}c"):
                v = cell.find(f"{SS}v")
                if v is None or v.text is None:
                    values.append("")
                    continue
                if cell.attrib.get("t") == "s":
                    idx = int(v.text)
                    values.append(strings[idx] if 0 <= idx < len(strings) else v.text)
                else:
                    values.append(v.text)
            rows.append(values)
        return rows
