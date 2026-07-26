from __future__ import annotations

import base64
import io
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
import pytest

from integration.qwen_remote_backend import OpenAICompatibleQwenVLBackend


class FakeCompletions:
    def __init__(self, content: str = '{"action":"STOP"}') -> None:
        self.content = content
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class FakeClient:
    def __init__(self, content: str = '{"action":"STOP"}') -> None:
        self.completions = FakeCompletions(content)
        self.chat = SimpleNamespace(completions=self.completions)
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_backend_sends_compressed_image_and_prompt_to_openai_compatible_client(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "wide.png"
    Image.new("RGB", (120, 60), (10, 20, 30)).save(image_path)
    client = FakeClient(" model output ")
    backend = OpenAICompatibleQwenVLBackend(
        base_url="http://example.invalid/v1",
        api_key="not-used-by-fake",
        model="qwen2.5-vl-test",
        max_tokens=77,
        image_max_side=40,
        jpeg_quality=70,
        client=client,
    )

    result = backend.generate(prompt="strict prompt", image_path=image_path)

    assert result == "model output"
    call = client.completions.calls[0]
    assert call["model"] == "qwen2.5-vl-test"
    assert call["temperature"] == 0.0
    assert call["max_tokens"] == 77
    content = call["messages"][0]["content"]  # type: ignore[index]
    assert content[1] == {"type": "text", "text": "strict prompt"}
    data_url = content[0]["image_url"]["url"]
    prefix = "data:image/jpeg;base64,"
    assert data_url.startswith(prefix)
    with Image.open(io.BytesIO(base64.b64decode(data_url[len(prefix):]))) as encoded:
        assert encoded.size == (40, 20)

    backend.close()
    assert client.closed


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (SimpleNamespace(choices=[]), "no completion choices"),
        (
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=""))]
            ),
            "empty response",
        ),
    ],
)
def test_backend_rejects_missing_completion_content(
    tmp_path: Path,
    response: object,
    message: str,
) -> None:
    class ResponseCompletions:
        def create(self, **_: object) -> object:
            return response

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=ResponseCompletions())
    )
    backend = OpenAICompatibleQwenVLBackend(
        base_url="http://example.invalid/v1",
        api_key="unused",
        client=client,
    )

    with pytest.raises(RuntimeError, match=message):
        backend.generate(prompt="prompt", image_path=None)


def test_backend_validates_image_path_and_constructor_options(tmp_path: Path) -> None:
    client = FakeClient()
    with pytest.raises(ValueError, match="jpeg_quality"):
        OpenAICompatibleQwenVLBackend(
            base_url="http://example.invalid/v1",
            api_key="unused",
            jpeg_quality=0,
            client=client,
        )
    backend = OpenAICompatibleQwenVLBackend(
        base_url="http://example.invalid/v1",
        api_key="unused",
        client=client,
    )
    with pytest.raises(FileNotFoundError):
        backend.generate(prompt="prompt", image_path=tmp_path / "missing.jpg")
