import base64
import json
import urllib.request
from abc import ABC, abstractmethod

from document_crawler.settings import VlmSettings

from .sniff import sniff_ext


class Vlm(ABC):
    """Görüntü byte'ından metin. Reader değil: sniff / children / tree yok."""

    @abstractmethod
    def read(self, image: bytes) -> str:
        """Bu görüntünün metni. Recursion yok."""
        pass


class HttpVlm(Vlm):
    """OpenAI uyumlu chat completions: VLM_URL + VLM_API_KEY."""

    def __init__(self, settings: VlmSettings | None = None, model: str = "gpt-4o-mini"):
        self.settings = settings or VlmSettings()
        self.model = model

    def read(self, image: bytes) -> str:
        mime = _image_mime(image)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all visible text from this image. Reply with text only.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{base64.b64encode(image).decode('ascii')}",
                            },
                        },
                    ],
                }
            ],
        }
        request = urllib.request.Request(
            self.settings.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            body = json.loads(response.read().decode("utf-8"))
        return (body["choices"][0]["message"]["content"] or "").strip()


def _image_mime(data: bytes) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".gif": "image/gif",
        ".tiff": "image/tiff",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
    }.get(sniff_ext(data) or "", "image/jpeg")
