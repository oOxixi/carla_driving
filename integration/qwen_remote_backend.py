from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any


class OpenAICompatibleQwenVLBackend:
    """通过 OpenAI 兼容接口调用远端 Qwen2.5-VL。

    该类只负责：
    1. 压缩并编码图像；
    2. 发送 prompt 和图像；
    3. 返回模型原始文本。

    JSON 校验、安全边界和命令转换仍由仓库现有模块负责。
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str = "qwen2.5-vl",
        timeout_s: float = 8.0,
        max_tokens: int = 192,
        image_max_side: int = 768,
        jpeg_quality: int = 75,
        client: Any | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url must not be empty")
        if not model.strip():
            raise ValueError("model must not be empty")
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if image_max_side <= 0:
            raise ValueError("image_max_side must be positive")
        if not 1 <= jpeg_quality <= 95:
            raise ValueError("jpeg_quality must be in [1, 95]")

        if client is None:
            try:
                from openai import OpenAI
            except ImportError as error:
                raise RuntimeError(
                    "remote Qwen requires the optional openai client; "
                    "install requirements-qwen-client.txt"
                ) from error
            client = OpenAI(
                base_url=base_url.rstrip("/"),
                api_key=api_key,
                timeout=timeout_s,
                max_retries=0,
            )
        self._client = client
        self._model = model
        self._max_tokens = max_tokens
        self._image_max_side = image_max_side
        self._jpeg_quality = jpeg_quality

    def generate(
        self,
        *,
        prompt: str,
        image_path: Path | None,
    ) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")

        content: list[dict[str, object]] = []

        if image_path is not None:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": self._image_to_data_url(image_path),
                    },
                }
            )

        content.append(
            {
                "type": "text",
                "text": prompt,
            }
        )

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
            temperature=0.0,
            max_tokens=self._max_tokens,
        )

        choices = getattr(response, "choices", None)
        if not choices:
            raise RuntimeError("Qwen server returned no completion choices")
        message = getattr(choices[0], "message", None)
        text = getattr(message, "content", None)
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Qwen server returned an empty response")

        return text.strip()

    def _image_to_data_url(self, image_path: Path) -> str:
        try:
            from PIL import Image
        except ImportError as error:
            raise RuntimeError(
                "remote Qwen image encoding requires Pillow"
            ) from error
        path = Path(image_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Qwen image not found: {path}")

        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail(
                (self._image_max_side, self._image_max_side),
                Image.Resampling.LANCZOS,
            )

            buffer = io.BytesIO()
            image.save(
                buffer,
                format="JPEG",
                quality=self._jpeg_quality,
                optimize=True,
            )

        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if callable(close):
            close()


__all__ = ["OpenAICompatibleQwenVLBackend"]
