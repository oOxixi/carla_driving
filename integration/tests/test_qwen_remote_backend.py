from __future__ import annotations

import base64
import io
import math
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw
import pytest

from integration.qwen_boundary import QwenInputContext
from integration.qwen_remote_backend import OpenAICompatibleQwenVLBackend


class FakeCompletions:
    def __init__(self, content: str = "B", confidence: float = 0.9) -> None:
        self.content = content
        self.confidence = confidence
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content=self.content),
                logprobs=SimpleNamespace(content=[SimpleNamespace(
                    token=self.content,
                    logprob=math.log(self.confidence),
                )]),
            )]
        )


class FakeClient:
    def __init__(self, content: str = "B", confidence: float = 0.9) -> None:
        self.completions = FakeCompletions(content, confidence)
        self.chat = SimpleNamespace(completions=self.completions)
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _context(detected_objects: list[dict[str, object]] | None = None) -> QwenInputContext:
    return QwenInputContext(
        request_id="remote-choice",
        frame=1,
        sim_time_s=0.05,
        voice_command="停车",
        rgb_ref=None,
        scene_state={"speed_mps": 2.0},
        perception={
            "visual_valid": True,
            "detected_objects": detected_objects or [],
        },
        safety_state={"recommended_action": "KEEP_SPEED"},
    )


def test_backend_requests_one_constrained_action_from_vllm(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "scene.png"
    image = Image.new("RGB", (100, 100), (5, 5, 5))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 30, 30), fill=(240, 10, 10))
    draw.rectangle((70, 70, 90, 90), fill=(10, 240, 10))
    image.save(image_path)
    detected_objects = [
        {
            "class": "vehicle",
            "confidence": 0.9,
            "distance_m": 5.0,
            "bbox_xyxy_norm": [0.1, 0.1, 0.3, 0.3],
        },
        {
            "class": "pedestrian",
            "confidence": 0.8,
            "distance_m": 8.0,
            "bbox_xyxy_norm": [0.7, 0.7, 0.9, 0.9],
        },
    ]
    client = FakeClient("B", confidence=0.9)
    backend = OpenAICompatibleQwenVLBackend(
        base_url="http://example.invalid/v1",
        api_key="not-used-by-fake",
        model="Qwen/Qwen3.5-2B-test",
        jpeg_quality=70,
        client=client,
    )

    result = backend.generate_action(
        prompt="choice prompt",
        image_path=image_path,
        context=_context(detected_objects),
    )

    assert result.code == "B"
    assert result.action == "STOP"
    assert result.confidence == pytest.approx(0.9)
    call = client.completions.calls[0]
    assert call["model"] == "Qwen/Qwen3.5-2B-test"
    assert call["temperature"] == 0.0
    assert call["max_tokens"] == 1
    assert call["logprobs"] is True
    assert call["top_logprobs"] == 5
    assert call["extra_body"] == {
        "structured_outputs": {"choice": ["A", "B", "C", "D", "E"]},
        "chat_template_kwargs": {"enable_thinking": False},
    }
    content = call["messages"][0]["content"]  # type: ignore[index]
    assert content[1] == {"type": "text", "text": "choice prompt"}
    data_url = content[0]["image_url"]["url"]
    prefix = "data:image/jpeg;base64,"
    assert data_url.startswith(prefix)
    with Image.open(io.BytesIO(base64.b64decode(data_url[len(prefix):]))) as encoded:
        encoded = encoded.convert("RGB")
        assert encoded.size == (256, 256)
        left_target = encoded.getpixel((64, 200))
        right_target = encoded.getpixel((192, 200))
        assert left_target[0] > left_target[1] * 4
        assert right_target[1] > right_target[0] * 4
    assert backend.last_visual_metadata == {
        "strategy": "scene_plus_focus_montage",
        "output_size": [256, 256],
        "focus_regions": 2,
    }

    backend.close()
    assert client.closed


def test_backend_defaults_match_qwen35_a800_profile(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "large.png"
    Image.new("RGB", (896, 448), (10, 20, 30)).save(image_path)
    client = FakeClient("B")
    backend = OpenAICompatibleQwenVLBackend(
        base_url="http://example.invalid/v1",
        api_key="unused",
        client=client,
    )

    result = backend.generate_action(
        prompt="choice prompt",
        image_path=image_path,
        context=_context(),
    )

    call = client.completions.calls[0]
    assert call["model"] == "Qwen/Qwen3.5-2B"
    assert call["max_tokens"] == 1
    assert result.action == "STOP"
    content = call["messages"][0]["content"]  # type: ignore[index]
    data_url = content[0]["image_url"]["url"]
    prefix = "data:image/jpeg;base64,"
    with Image.open(io.BytesIO(base64.b64decode(data_url[len(prefix):]))) as encoded:
        assert encoded.size == (256, 256)


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
        backend.generate_action(
            prompt="prompt",
            image_path=None,
            context=_context(),
        )


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
        backend.generate_action(
            prompt="prompt",
            image_path=tmp_path / "missing.jpg",
            context=_context(),
        )


def test_backend_rejects_non_single_token_budget() -> None:
    with pytest.raises(ValueError, match="max_tokens must be 1"):
        OpenAICompatibleQwenVLBackend(
            base_url="http://example.invalid/v1",
            api_key="unused",
            max_tokens=2,
            client=FakeClient(),
        )
