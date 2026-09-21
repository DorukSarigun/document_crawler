import io
import json
from pathlib import Path

from PIL import Image

from document_crawler import Block, HttpVlm, ImageReader, Processor, Vlm, VlmSettings, default_readers


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), (255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


PNG = _png()


class FakeVlm(Vlm):
    def __init__(self):
        self.calls = 0

    def read(self, image: bytes) -> str:
        self.calls += 1
        return f"vlm:{len(image)}"


def _no_image_readers() -> list:
    return [r for r in default_readers() if not isinstance(r, ImageReader)]


def test_vlm_settings_from_env(monkeypatch):
    monkeypatch.setenv("VLM_API_KEY", "secret")
    monkeypatch.setenv("VLM_URL", "http://127.0.0.1/v1/chat/completions")
    monkeypatch.setenv("VLM_QUALITY", "45")
    settings = VlmSettings()
    assert settings.api_key == "secret"
    assert settings.url == "http://127.0.0.1/v1/chat/completions"
    assert settings.quality == 45.0


def test_process_image_file_uses_vlm_without_image_reader(tmp_path: Path):
    path = tmp_path / "x.png"
    path.write_bytes(PNG)
    vlm = FakeVlm()
    proc = Processor(readers=_no_image_readers(), vlm=vlm)
    node = proc.process(path)
    assert vlm.calls == 1
    assert node.blocks[0].content == f"vlm:{len(PNG)}"


def test_collect_images_when_only_vlm(tmp_path: Path):
    path = tmp_path / "x.png"
    path.write_bytes(PNG)
    proc = Processor(readers=_no_image_readers(), vlm=FakeVlm())
    assert proc.collect_files(tmp_path) == [path]


def test_finish_uses_vlm_when_image_reader_missing():
    vlm = FakeVlm()
    proc = Processor(readers=_no_image_readers(), vlm=vlm)
    out = proc._finish(Block("image", PNG, order=(1, 0)))
    assert out.kind == "image"
    assert out.content == f"vlm:{len(PNG)}"
    assert vlm.calls == 1


def test_low_ocr_quality_triggers_vlm():
    vlm = FakeVlm()
    proc = Processor(vlm=vlm, vlm_quality=60)
    proc.image_reader.ocr = lambda data: ("weak", 12.0)
    out = proc._finish(Block("image", PNG, order=(1, 0)))
    assert out.content == f"vlm:{len(PNG)}"
    assert vlm.calls == 1


def test_high_ocr_quality_keeps_tesseract():
    vlm = FakeVlm()
    proc = Processor(vlm=vlm, vlm_quality=60)
    proc.image_reader.ocr = lambda data: ("clear text", 88.0)
    out = proc._finish(Block("image", PNG, order=(1, 0)))
    assert out.content == "clear text"
    assert vlm.calls == 0


def test_quality_equal_to_threshold_keeps_tesseract():
    vlm = FakeVlm()
    proc = Processor(vlm=vlm, vlm_quality=60)
    proc.image_reader.ocr = lambda data: ("border", 60.0)
    out = proc._finish(Block("image", PNG, order=(1, 0)))
    assert out.content == "border"
    assert vlm.calls == 0


def test_standalone_image_uses_vlm_when_ocr_weak(tmp_path: Path):
    path = tmp_path / "x.png"
    path.write_bytes(PNG)
    vlm = FakeVlm()
    proc = Processor(vlm=vlm, vlm_quality=60)
    proc.image_reader.ocr = lambda data: ("", 0.0)
    node = proc.process(path)
    assert vlm.calls == 1
    assert node.blocks[0].content == f"vlm:{len(PNG)}"


def test_http_vlm_posts_url_and_key(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "hello from vlm"}}]}
            ).encode()

    def fake_urlopen(request):
        captured["url"] = request.full_url
        captured["auth"] = request.get_header("Authorization")
        captured["body"] = json.loads(request.data.decode())
        return FakeResponse()

    monkeypatch.setattr("document_crawler.readers.vlm.urllib.request.urlopen", fake_urlopen)
    settings = VlmSettings(api_key="k", url="http://127.0.0.1/v1/chat/completions")
    text = HttpVlm(settings).read(PNG)
    assert text == "hello from vlm"
    assert captured["url"] == "http://127.0.0.1/v1/chat/completions"
    assert captured["auth"] == "Bearer k"
    assert captured["body"]["model"] == "gpt-4o-mini"
