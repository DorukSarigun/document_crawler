from pathlib import Path

import pytest

from tests.conftest import DATA, all_text, iter_nodes, tree_stats

FIXTURES = {
    "synthetic_pdf": DATA / "pdf/mixed_layout/synthetic_para_image_para.pdf",
    "invoice_pdf": DATA / "nested/handmade/invoice_with_attachments.pdf",
    "docx_xlsx": DATA / "nested/local/docx_embedded_xlsx.docx",
    "embedded_pdf_docx": DATA / "nested/tika/EmbeddedPDF.docx",
    "excel_pdf": DATA / "nested/tika/testExcel_embeddedPDF.xlsx",
    "pdf_package": DATA / "nested/tika/testPDFPackage.pdf",
    "eml_zip": DATA / "nested/handmade/mail_with_zip_of_pdf.eml",
    "having_images": DATA / "docx/having-images.docx",
}


@pytest.fixture(scope="session")
def trees(processor):
    missing = [k for k, p in FIXTURES.items() if not p.exists()]
    if missing:
        pytest.skip(f"eksik fixture: {missing}")
    return {key: processor.process(path) for key, path in FIXTURES.items()}


def test_fixtures_exist():
    missing = [str(p) for p in FIXTURES.values() if not p.exists()]
    assert not missing, missing


def test_synthetic_reading_order(trees):
    node = trees["synthetic_pdf"]
    kinds = [b.kind for b in node.blocks]
    assert kinds == ["text", "text", "image", "text", "text", "image", "text", "text"]
    text = all_text(node)
    assert "first paragraph" in text
    assert "second paragraph" in text
    assert "third paragraph" in text
    assert "Figure 1" in text
    assert "Figure 2" in text
    images = [b for b in node.blocks if b.kind == "image"]
    assert len(images) == 2
    assert any("BOOK" in (b.content or "") or "TAMAN" in (b.content or "") for b in images)


def test_invoice_page_and_attachments(trees):
    node = trees["invoice_pdf"]
    text = all_text(node)
    assert "Outer PDF" in text
    names = [c.name for c in node.children]
    assert names == ["packing_list.txt", "receipt.jpg", "filesamples_sample3.xlsx"]
    assert "item A" in all_text(node.children[0])
    assert "item B" in all_text(node.children[0])
    receipt = all_text(node.children[1])
    assert len(receipt) > 10
    xlsx = all_text(node.children[2])
    assert "Sheet1" in xlsx
    assert "Months" in xlsx


def test_docx_embedded_xlsx(trees):
    node = trees["docx_xlsx"]
    assert node.children
    child = node.children[0]
    assert child.name.endswith(".xlsx")
    assert "Series 1" in all_text(child)


def test_word_ole_unwraps_to_pdf(trees):
    node = trees["embedded_pdf_docx"]
    names = [n.name for n in iter_nodes(node)]
    assert any(n.endswith(".bin") for n in names)
    assert "payload.pdf" in names
    text = all_text(node)
    assert "Test Document" in text
    assert "Word Document" in text or "pdf" in text.lower()


def test_xlsx_embedded_pdf(trees):
    node = trees["excel_pdf"]
    names = [n.name for n in iter_nodes(node)]
    assert any("oleObject" in n or n.endswith(".bin") for n in names)
    assert any(n.endswith(".pdf") for n in names)


def test_pdf_package_has_two_child_pdfs(trees):
    node = trees["pdf_package"]
    pdf_children = [c for c in node.children if c.name.lower().endswith(".pdf")]
    assert len(pdf_children) == 2
    for child in pdf_children:
        assert tree_stats(child)["texts"] >= 1


def test_eml_zip_pdf_chain(trees):
    node = trees["eml_zip"]
    text = all_text(node)
    assert "Subject:" in text
    names = [n.name for n in iter_nodes(node)]
    assert "bundle_pdf_docx_csv.zip" in names
    assert "invoice_with_attachments.pdf" in names
    assert "packing_list.txt" in names
    assert "titanic.csv" in names
    assert "item A" in text
    assert "PassengerId" in text


def test_docx_layout_images_ocr(trees):
    node = trees["having_images"]
    images = [b for b in node.blocks if b.kind == "image"]
    assert images, "word/media image blokları parse'ta olmalı"
    assert any(isinstance(b.content, str) and len(b.content) > 0 for b in images)


def test_no_raw_image_bytes_left_after_ocr(trees):
    leftover = []
    for key, node in trees.items():
        for item in iter_nodes(node):
            for block in item.blocks:
                if block.kind == "image" and isinstance(block.content, bytes):
                    leftover.append(f"{key}:{item.name}")
    assert leftover == []


def test_detect_routes_all_registered_extensions(processor):
    for reader in processor.readers:
        for ext in reader.extension:
            got = processor.detect(f"file{ext}")
            assert got is reader, ext


def test_process_and_parse_accept_bytes(processor):
    path = FIXTURES["synthetic_pdf"]
    data = path.read_bytes()
    assert processor.detect(data) is not None
    assert processor.detect(data).__class__.__name__ == "PdfReader"

    from_path = processor.process(path)
    from_bytes = processor.process(data)
    assert [b.kind for b in from_path.blocks] == [b.kind for b in from_bytes.blocks]
    assert any(b.kind == "text" and "first paragraph" in str(b.content) for b in from_bytes.blocks)

    pdf_reader = processor.detect(data)
    blocks = pdf_reader.parse(data)
    kids = pdf_reader.children(data)
    assert blocks
    assert kids == []
