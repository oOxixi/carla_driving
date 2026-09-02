from __future__ import annotations

import base64
import io
import math
from pathlib import Path
from typing import Any

from .qwen_boundary import QwenInputContext
from .qwen_profiles import (
    QwenModelProfile,
    get_qwen_profile_by_model,
    resolve_qwen_profile,
)
from .qwen_vl_adapter import QwenVLActionChoice


class OpenAICompatibleQwenVLBackend:
    """Ask a vLLM-compatible Qwen3-VL endpoint for one action code.

    Final Schema assembly, target grounding and safety overrides stay in the
    repository-owned strict adapter rather than autoregressive model output.
    """

    def __init__(
        self,
        *,
        base_url: str,
        profile: QwenModelProfile | None = None,
        api_key: str = "local-offline",
        timeout_s: float = 30.0,
        max_tokens: int = 1,
        model: str | None = None,
        image_max_side: int | None = None,
        jpeg_quality: int = 75,
        client: Any | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url must not be empty")
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        if max_tokens != 1:
            raise ValueError("max_tokens must be 1 for constrained action choice")
        if not 1 <= jpeg_quality <= 95:
            raise ValueError("jpeg_quality must be in [1, 95]")

        self.profile = profile or (
            get_qwen_profile_by_model(model)
            if model is not None
            else resolve_qwen_profile(None)
        )
        if model is not None and model != self.profile.model:
            raise ValueError("model must match the selected Qwen profile")
        if image_max_side is not None and image_max_side != self.profile.image_max_side:
            raise ValueError("image_max_side must match the selected Qwen profile")

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
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.prompt_style = self.profile.prompt_style
        self._model = self.profile.model
        self._max_tokens = max_tokens
        self._image_max_side = self.profile.image_max_side
        self._jpeg_quality = jpeg_quality
        self.last_visual_metadata: dict[str, object] | None = None

    def generate_action(
        self,
        *,
        prompt: str,
        image_path: Path | None,
        context: QwenInputContext,
    ) -> QwenVLActionChoice:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        if not isinstance(context, QwenInputContext):
            raise TypeError("context must be QwenInputContext")

        content: list[dict[str, object]] = []

        if image_path is not None:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": self._image_to_data_url(image_path, context),
                    },
                }
            )
        else:
            self.last_visual_metadata = None

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
            logprobs=True,
            top_logprobs=5,
            extra_body={
                "structured_outputs": {
                    "choice": ["A", "B", "C", "D", "E"],
                },
                "chat_template_kwargs": {"enable_thinking": False},
                "mm_processor_kwargs": {
                    "min_pixels": self.profile.visual_tokens * 28 * 28,
                    "max_pixels": self.profile.visual_tokens * 28 * 28,
                },
            },
        )

        choices = getattr(response, "choices", None)
        if not choices:
            raise RuntimeError("Qwen server returned no completion choices")
        message = getattr(choices[0], "message", None)
        text = getattr(message, "content", None)
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Qwen server returned an empty response")

        code = text.strip().upper()
        confidence = _first_token_confidence(choices[0], code)
        try:
            return QwenVLActionChoice.from_code(code, confidence)
        except ValueError as error:
            raise RuntimeError(f"Qwen server returned invalid action code: {code!r}") from error

    def _image_to_data_url(
        self,
        image_path: Path,
        context: QwenInputContext,
    ) -> str:
        try:
            from PIL import Image, ImageOps
        except ImportError as error:
            raise RuntimeError(
                "remote Qwen image encoding requires Pillow"
            ) from error
        path = Path(image_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Qwen image not found: {path}")

        with Image.open(path) as image:
            image = image.convert("RGB")
            image = _scene_focus_montage(
                image,
                context.perception.get("detected_objects", []),
                size=self._image_max_side,
                image_ops=ImageOps,
            )
            self.last_visual_metadata = {
                "strategy": "scene_plus_focus_montage",
                "output_size": [self._image_max_side, self._image_max_side],
                "focus_regions": _valid_focus_count(
                    context.perception.get("detected_objects", [])
                ),
            }

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


def _first_token_confidence(choice: object, expected_code: str) -> float:
    logprobs = getattr(choice, "logprobs", None)
    entries = getattr(logprobs, "content", None)
    if not entries:
        raise RuntimeError("Qwen server returned no token logprobs")
    selected = next(
        (
            entry
            for entry in entries
            if str(getattr(entry, "token", "")).strip().upper() == expected_code
        ),
        entries[0],
    )
    value = getattr(selected, "logprob", None)
    if (
        type(value) not in (int, float)
        or isinstance(value, bool)
        or math.isnan(float(value))
    ):
        raise RuntimeError("Qwen server returned an invalid token logprob")
    if float(value) == -math.inf:
        return 0.0
    if not math.isfinite(float(value)):
        raise RuntimeError("Qwen server returned an invalid token logprob")
    return max(0.0, min(1.0, math.exp(float(value))))


def _scene_focus_montage(
    image: Any,
    detected_objects: object,
    *,
    size: int,
    image_ops: Any,
) -> Any:
    from PIL import Image

    top_height = round(size * 0.5625)
    bottom_height = size - top_height
    canvas = Image.new("RGB", (size, size), (16, 16, 16))
    overview = image_ops.contain(
        image,
        (size, top_height),
        method=Image.Resampling.LANCZOS,
    )
    canvas.paste(
        overview,
        ((size - overview.width) // 2, (top_height - overview.height) // 2),
    )

    focus_regions = _focus_regions(image, detected_objects)
    if focus_regions:
        slot_width = size // len(focus_regions)
        for index, region in enumerate(focus_regions):
            width = size - slot_width * index if index == len(focus_regions) - 1 else slot_width
            focused = image_ops.fit(
                region,
                (width, bottom_height),
                method=Image.Resampling.LANCZOS,
            )
            canvas.paste(focused, (slot_width * index, top_height))
    else:
        width, height = image.size
        road = image.crop((0, round(height * 0.35), width, height))
        road = image_ops.fit(
            road,
            (size, bottom_height),
            method=Image.Resampling.LANCZOS,
        )
        canvas.paste(road, (0, top_height))
    return canvas


def _focus_regions(image: Any, detected_objects: object) -> list[Any]:
    if not isinstance(detected_objects, list):
        return []
    ranked: list[tuple[float, float, tuple[float, float, float, float]]] = []
    for item in detected_objects:
        if not isinstance(item, dict):
            continue
        box = _normalized_box(item.get("bbox_xyxy_norm"))
        if box is None:
            continue
        distance = item.get("distance_m")
        confidence = item.get("confidence")
        distance_key = (
            float(distance)
            if type(distance) in (int, float)
            and not isinstance(distance, bool)
            and math.isfinite(float(distance))
            else math.inf
        )
        confidence_key = (
            -float(confidence)
            if type(confidence) in (int, float)
            and not isinstance(confidence, bool)
            and math.isfinite(float(confidence))
            else 0.0
        )
        ranked.append((distance_key, confidence_key, box))
    ranked.sort(key=lambda item: (item[0], item[1]))

    width, height = image.size
    regions = []
    for _, __, (x1, y1, x2, y2) in ranked[:2]:
        pad_x = (x2 - x1) * 0.12
        pad_y = (y2 - y1) * 0.12
        left = max(0, math.floor((x1 - pad_x) * width))
        top = max(0, math.floor((y1 - pad_y) * height))
        right = min(width, math.ceil((x2 + pad_x) * width))
        bottom = min(height, math.ceil((y2 + pad_y) * height))
        if right > left and bottom > top:
            regions.append(image.crop((left, top, right, bottom)))
    return regions


def _valid_focus_count(detected_objects: object) -> int:
    if not isinstance(detected_objects, list):
        return 0
    return min(
        2,
        sum(
            1
            for item in detected_objects
            if isinstance(item, dict)
            and _normalized_box(item.get("bbox_xyxy_norm")) is not None
        ),
    )


def _normalized_box(value: object) -> tuple[float, float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    if any(
        type(item) not in (int, float)
        or isinstance(item, bool)
        or not math.isfinite(float(item))
        for item in value
    ):
        return None
    x1, y1, x2, y2 = (float(item) for item in value)
    if not (0.0 <= x1 < x2 <= 1.0 and 0.0 <= y1 < y2 <= 1.0):
        return None
    return x1, y1, x2, y2


__all__ = ["OpenAICompatibleQwenVLBackend"]
