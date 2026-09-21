# document-crawler

Dosyayı koklar (magic + uzantı), uygun reader’a yollar, gömülü dosyaları açar, okuma sırasına göre metin çıkarır.

İki kullanım:

- **CLI** — varsayılan reader seti, `python -m document_crawler`
- **Kütüphane** — `Processor(readers=...)` ile kendi reader / VLM

## Gereksinimler

- Python 3.10+
- [Tesseract](https://github.com/tesseract-ocr/tesseract) (ImageReader OCR için sistem paketi)

## Kurulum

Repo kökünden:

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

Geliştirme:

```bash
uv pip install -e ".[dev]"
```

Başka bir projede:

```bash
uv pip install /path/to/Document_crawler
```

```python
from document_crawler import Processor
```

Komutlar paket üzerinden çalışır (`document_crawler/__main__.py`). `main.py` yok. Editable kuruluysa herhangi bir klasörden; değilse repo kökünden `python -m document_crawler`.

## CLI

```bash
python -m document_crawler --help
```

| Komut | İş |
|---|---|
| `crawl` | Klasörü tara, `crawled.json` yaz |
| `extract_file_content` | Tek dosya çıkar |
| `search_and_extract` | Önce `crawl`, sonra her dosya için `extract_file_content` |

`--ext` yalnızca **diskteki ana dosyayı** süzer. İçerideki ekler (PDF embfile, zip, OLE) süzülmez.

```bash
python -m document_crawler search_and_extract \
  /path/to/data \
  /path/to/output/extracted
```

```bash
python -m document_crawler crawl /path/to/data --dest output/crawled.json --ext pdf --ext docx
```

```bash
python -m document_crawler extract_file_content invoice.pdf --dest out.txt
python -m document_crawler extract_file_content invoice.pdf --write-json --dest out.json
python -m document_crawler extract_file_content invoice.pdf --print-tree
```

`search_and_extract` çıktıda `crawled.json` ve her dosya için `.txt` (veya `--write-json` ile `.json`) üretir. Gömülü içerik ayrı dosya değil; üst dosyanın metnine sırayla eklenir.

CLI her zaman `Processor()` kullanır. Kendi reader’ın için aşağıdaki kütüphane API’si.

## Ayarlar (`.env`)

Çalışma dizinindeki `.env` (`VlmSettings`, prefix `VLM_`):

```
VLM_API_KEY=
VLM_URL=
VLM_QUALITY=60
```

`VLM_URL` tam chat-completions adresi olsun, örneğin `https://api.openai.com/v1/chat/completions`.

Görüntü metni önce Tesseract. Ortalama güven `VLM_QUALITY` altındaysa (0–100) `HttpVlm` çağrılır. ImageReader yoksa doğrudan VLM. Key veya URL boşsa VLM kurulmaz; Tesseract sonucu kalır.

## Kütüphane

```python
from document_crawler import Processor

proc = Processor()
node = proc.process("invoice.pdf")
node.print_tree()
proc.write_txt(node, "out.txt")
proc.write(node, "out.json")
```

`process` path veya `bytes` alır (`name=` ile).

### Kendi reader

`Reader.parse` bu katmanın içeriği (recursion yok). `children` gömülü dosyalar (layout image değil). `Processor` children’da recurse eder.

```python
from document_crawler import Block, Processor, Reader, default_readers


class HtmlReader(Reader):
    extension = (".html", ".htm")

    def parse(self, file):
        text = self.load(file).decode("utf-8", errors="replace")
        return [Block("text", text, order=(0,))]

    def children(self, data):
        return []


proc = Processor(readers=[*default_readers(), HtmlReader()])
```

Aynı uzantıda listede **sonra gelen** kazanır. İstemediğini listeden çıkar:

```python
from document_crawler import ImageReader, Processor, default_readers, HttpVlm

readers = [r for r in default_readers() if not isinstance(r, ImageReader)]
proc = Processor(readers=readers, vlm=HttpVlm(), vlm_quality=50)
```

Kendi VLM: `Vlm.read(image: bytes) -> str`.

## Model

| Tip | Anlam |
|---|---|
| `File` | Disk path veya ham byte |
| `Reader` | Bir format: `parse` + `children` |
| `Block` | Okuma sırasındaki parça (`text` / `image` / `table`) |
| `Node` | Ağaçtaki bir dosya: `blocks` + `children` |
| `Processor` | Detect → parse → image OCR/VLM → recurse |
| `Vlm` | Sadece görüntü → metin; sniff/ağaç yok |

Detect sırası: dosya uzantısı, yoksa magic sniff.

Varsayılan reader’lar: PDF, DOCX, XLSX, PPTX, görüntü, metin, EML, ZIP, OLE.

## Test

```bash
pytest
```
