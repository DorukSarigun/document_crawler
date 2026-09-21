import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from document_crawler import Processor
from document_crawler.__main__ import app, parse_extensions
from tests.conftest import DATA, all_text

runner = CliRunner()

NESTED = DATA / "nested"
HANDMADE = NESTED / "handmade"
SYNTHETIC = DATA / "pdf/mixed_layout/synthetic_para_image_para.pdf"
INVOICE = HANDMADE / "invoice_with_attachments.pdf"
EML = HANDMADE / "mail_with_zip_of_pdf.eml"


@pytest.fixture
def tmp_out(tmp_path: Path) -> Path:
    return tmp_path


def test_parse_extensions():
    assert parse_extensions(None) is None
    assert parse_extensions(["png"]) == {".png"}
    assert parse_extensions([".PNG", "jpg,docx"]) == {".png", ".jpg", ".docx"}


def test_collect_files_ext_filters_only_root():
    proc = Processor()
    pdfs = proc.collect_files(NESTED, extensions={".pdf"})
    assert pdfs
    assert all(p.suffix.lower() == ".pdf" for p in pdfs)
    assert INVOICE in pdfs
    assert EML not in pdfs

    pngs = proc.collect_files(DATA / "images", extensions={".png"})
    assert pngs
    assert all(p.suffix.lower() == ".png" for p in pngs)


def test_process_nested_children_despite_root_ext_filter():
    proc = Processor()
    node = proc.process(INVOICE)
    names = [c.name for c in node.children]
    assert "receipt.jpg" in names
    assert "filesamples_sample3.xlsx" in names
    text = proc._blocks_text(node)
    assert "item A" in text
    assert "Outer PDF" in text


def test_write_txt_is_reading_order(tmp_out: Path):
    proc = Processor()
    node = proc.process(SYNTHETIC)
    dest = tmp_out / "order.txt"
    proc.write_txt(node, dest)
    body = dest.read_text(encoding="utf-8")
    i1 = body.index("first paragraph")
    i2 = body.index("Figure 1")
    i3 = body.index("second paragraph")
    i4 = body.index("third paragraph")
    assert i1 < i2 < i3 < i4


def test_cli_crawl_writes_manifest(tmp_out: Path):
    dest = tmp_out / "crawled.json"
    result = runner.invoke(app, ["crawl", str(HANDMADE), "--dest", str(dest)])
    assert result.exit_code == 0, result.output
    manifest = json.loads(dest.read_text())
    files = [Path(p) for p in manifest["files"]]
    names = {p.name for p in files}
    assert "invoice_with_attachments.pdf" in names
    assert "mail_with_zip_of_pdf.eml" in names
    assert manifest["root"] == str(HANDMADE.resolve())


def test_cli_crawl_ext_pdf_only(tmp_out: Path):
    dest = tmp_out / "crawled.json"
    result = runner.invoke(
        app, ["crawl", str(NESTED), "--dest", str(dest), "--ext", "pdf"]
    )
    assert result.exit_code == 0, result.output
    files = [Path(p) for p in json.loads(dest.read_text())["files"]]
    assert files
    assert all(p.suffix.lower() == ".pdf" for p in files)
    assert any(p.name == "invoice_with_attachments.pdf" for p in files)
    assert not any(p.suffix.lower() == ".eml" for p in files)


def test_cli_extract_file_txt(tmp_out: Path):
    dest = tmp_out / "invoice.txt"
    result = runner.invoke(
        app,
        ["extract_file_content", str(INVOICE), "--dest", str(dest)],
    )
    assert result.exit_code == 0, result.output
    text = dest.read_text(encoding="utf-8")
    assert "Outer PDF" in text
    assert "item A" in text
    assert "item B" in text
    assert "Sheet1" in text or "Months" in text


def test_cli_extract_file_json_tree(tmp_out: Path):
    dest = tmp_out / "invoice.json"
    result = runner.invoke(
        app,
        ["extract_file_content", str(INVOICE), "--write-json", "--dest", str(dest)],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(dest.read_text())
    assert data["name"] == INVOICE.name
    child_names = [c["name"] for c in data["children"]]
    assert "packing_list.txt" in child_names
    assert "receipt.jpg" in child_names
    texts = " ".join(b["content"] for b in data["blocks"] if isinstance(b.get("content"), str))
    assert "Outer PDF" in texts


def test_cli_search_and_extract_from_crawl(tmp_out: Path):
    extracted = tmp_out / "out"
    result = runner.invoke(
        app, ["search_and_extract", str(HANDMADE), str(extracted)]
    )
    assert result.exit_code == 0, result.output
    invoice_txt = extracted / "invoice_with_attachments.pdf.txt"
    eml_txt = extracted / "mail_with_zip_of_pdf.eml.txt"
    assert invoice_txt.exists()
    assert eml_txt.exists()
    invoice = invoice_txt.read_text(encoding="utf-8")
    assert "item A" in invoice
    eml = eml_txt.read_text(encoding="utf-8")
    assert "Subject:" in eml
    assert "PassengerId" in eml or "item A" in eml


def test_cli_search_and_extract_ext_does_not_drop_inner_content(tmp_out: Path):
    extracted = tmp_out / "out"
    result = runner.invoke(
        app, ["search_and_extract", str(HANDMADE), str(extracted), "--ext", "pdf"]
    )
    assert result.exit_code == 0, result.output
    txts = list(extracted.rglob("*.txt"))
    assert txts
    assert all(".eml" not in p.name for p in txts)
    body = "\n".join(p.read_text(encoding="utf-8") for p in txts)
    assert "item A" in body


def test_cli_extract_eml_chain(tmp_out: Path):
    dest = tmp_out / "mail.txt"
    result = runner.invoke(app, ["extract_file_content", str(EML), "--dest", str(dest)])
    assert result.exit_code == 0, result.output
    text = dest.read_text(encoding="utf-8")
    assert "Nested" in text or "Subject:" in text
    assert "item A" in text


def test_cli_extract_docx_embedded_xlsx(tmp_out: Path):
    path = DATA / "nested/local/docx_embedded_xlsx.docx"
    dest = tmp_out / "docx.txt"
    result = runner.invoke(app, ["extract_file_content", str(path), "--dest", str(dest)])
    assert result.exit_code == 0, result.output
    assert "Series 1" in dest.read_text(encoding="utf-8")


def test_cli_extract_ole_word_pdf(tmp_out: Path):
    path = DATA / "nested/tika/EmbeddedPDF.docx"
    dest = tmp_out / "ole.txt"
    result = runner.invoke(app, ["extract_file_content", str(path), "--dest", str(dest)])
    assert result.exit_code == 0, result.output
    text = dest.read_text(encoding="utf-8")
    assert "Test Document" in text
