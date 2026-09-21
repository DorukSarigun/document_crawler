import json
from pathlib import Path
from typing import Annotated

import typer

from document_crawler import Processor
from document_crawler.readers.processor import OUTPUT_DIR

app = typer.Typer()


def parse_extensions(exts: list[str] | None) -> set[str] | None:
    if not exts:
        return None
    out: set[str] = set()
    for item in exts:
        for part in item.split(","):
            part = part.strip().lower()
            if not part:
                continue
            out.add(part if part.startswith(".") else f".{part}")
    return out or None


@app.command(name="crawl")
def crawl(
    path: Annotated[str, typer.Argument(help="Klasör (veya tek dosya)")],
    dest: Annotated[Path | None, typer.Option("--dest", help="Manifest JSON")] = None,
    ext: Annotated[
        list[str] | None,
        typer.Option("--ext", help="Ana dosya uzantısı (iç ekler süzülmez)"),
    ] = None,
):
    processor = Processor()
    root = Path(path).resolve()
    extensions = parse_extensions(ext)
    files = processor.collect_files(root, extensions=extensions)
    payload = {
        "root": str(root),
        "extensions": sorted(extensions) if extensions else None,
        "files": [str(p) for p in files],
    }
    dest = dest or (OUTPUT_DIR / "crawled.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


@app.command(name="extract_file_content")
def extract_file_content(
    file_path: Annotated[str, typer.Argument(help="Tek dosya")],
    print_tree: Annotated[bool, typer.Option("--print-tree")] = False,
    write_json: Annotated[bool, typer.Option("--write-json")] = False,
    dest: Annotated[Path | None, typer.Option("--dest", help="Çıktı dosyası")] = None,
):
    processor = Processor()
    node = processor.process(file_path)
    if print_tree:
        node.print_tree()
    if write_json:
        processor.write(node, dest)
    else:
        processor.write_txt(node, dest)


@app.command(name="search_and_extract")
def search_and_extract(
    source_path: Annotated[str, typer.Argument(help="Taranacak klasör")],
    extraction_path: Annotated[str, typer.Argument(help="İçerik klasörü")],
    write_json: Annotated[bool, typer.Option("--write-json")] = False,
    ext: Annotated[
        list[str] | None,
        typer.Option("--ext", help="Ana dosya uzantısı (iç ekler süzülmez)"),
    ] = None,
):
    out_dir = Path(extraction_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = crawl(
        path=source_path,
        dest=out_dir / "crawled.json",
        ext=ext,
    )
    root = Path(payload["root"])
    suffix = ".json" if write_json else ".txt"
    for file_path in payload["files"]:
        path = Path(file_path)
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = Path(path.name)
        dest = out_dir / rel
        dest = dest.with_name(dest.name + suffix)
        dest.parent.mkdir(parents=True, exist_ok=True)
        extract_file_content(
            file_path=str(path),
            write_json=write_json,
            dest=dest,
        )


if __name__ == "__main__":
    app()
