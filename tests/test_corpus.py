from collections import defaultdict
from pathlib import Path

import pytest

from document_crawler import Processor
from tests.conftest import DATA, FastProcessor, all_text, tree_stats


def registered_extensions(processor: Processor) -> set[str]:
    return {ext.lower() for r in processor.readers for ext in r.extension}


def corpus_files() -> list[Path]:
    proc = FastProcessor()
    exts = registered_extensions(proc)
    return sorted(
        p
        for p in DATA.rglob("*")
        if p.is_file() and p.suffix.lower() in exts and p.stat().st_size > 0
    )


CORPUS = corpus_files()


@pytest.fixture(scope="session")
def corpus_results(fast_processor):
    results: dict[Path, tuple[str, object, str | None]] = {}
    for path in CORPUS:
        try:
            results[path] = ("ok", fast_processor.process(path), None)
        except Exception as exc:
            results[path] = ("error", None, f"{type(exc).__name__}: {exc}")
    return results


@pytest.mark.parametrize("path", CORPUS, ids=lambda p: str(p.relative_to(DATA)))
def test_file_yields_content(corpus_results, path: Path):
    status, node, err = corpus_results[path]
    if status == "error":
        pytest.fail(err)

    stats = tree_stats(node)
    text = all_text(node)
    ext = path.suffix.lower()
    assert node.name == path.name
    assert node.kind == ext.lstrip(".")

    if ext in {".bin", ".doc", ".xls", ".ppt", ".msg"}:
        pytest.skip("OLE yaprak: unwrap yoksa boş kalabilir")

    # parse çalıştıysa blok veya child yeter; OCR/boş şablon metni ayrı özetlenir
    has_payload = stats["blocks"] > 0 or stats["children"] > 0 or bool(text.strip())
    if not has_payload and ext in {".docx", ".pptx", ".pdf"}:
        pytest.skip(f"boş şablon olabilir: {path.name}")
    assert has_payload, f"içerik yok: {path} stats={stats}"


def test_corpus_summary(corpus_results, capsys):
    errors = []
    empty = []
    by_ext = defaultdict(lambda: {"ok": 0, "empty": 0, "error": 0, "chars": 0, "nodes": 0})

    for path, (status, node, err) in corpus_results.items():
        ext = path.suffix.lower()
        rel = str(path.relative_to(DATA))
        if status == "error":
            errors.append((rel, err))
            by_ext[ext]["error"] += 1
            continue
        stats = tree_stats(node)
        text = all_text(node)
        if not text.strip() and stats["images"] == 0 and stats["children"] == 0:
            empty.append(rel)
            by_ext[ext]["empty"] += 1
        else:
            by_ext[ext]["ok"] += 1
            by_ext[ext]["chars"] += stats["chars"]
            by_ext[ext]["nodes"] += stats["nodes"]

    print("\n=== corpus özet ===")
    print(
        f"dosya={len(CORPUS)}  ok={sum(v['ok'] for v in by_ext.values())}  "
        f"empty={len(empty)}  error={len(errors)}"
    )
    for ext in sorted(by_ext):
        row = by_ext[ext]
        print(
            f"  {ext:8} ok={row['ok']:4} empty={row['empty']:3} error={row['error']:3} "
            f"chars={row['chars']:8} nodes={row['nodes']:5}"
        )
    if empty:
        print("boş:")
        for rel in empty:
            print(f"  {rel}")
    if errors:
        print("hata:")
        for rel, msg in errors:
            print(f"  {rel}\n    {msg}")

    assert errors == [], f"{len(errors)} dosya patladı"
    empty_rate = len(empty) / max(len(CORPUS), 1)
    assert empty_rate < 0.15, f"çok fazla boş ağaç: {empty_rate:.1%} ({len(empty)})"
