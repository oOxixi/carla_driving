"""Local Qwen2.5-VL runtime used by Day22 real-model validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class Qwen25VLRuntime:
    """
    Qwen2.5-VL本地推理封装。

    模型只加载一次。generate()每次接收：
    - Day22提示词；
    - 可选CARLA RGB图片。

    返回Qwen原始文本，不执行车辆控制。
    """

    def __init__(
        self,
        model_path: str = "models/Qwen2.5-VL-7B",
        *,
        max_new_tokens: int = 192,
    ) -> None:
        model_dir = Path(model_path)

        if not model_dir.is_dir():
            raise FileNotFoundError(
                f"Qwen model directory not found: {model_dir}"
            )

        if max_new_tokens <= 0:
            raise ValueError("max_new_tokens must be positive")

        self.model_path = str(model_dir)
        self.max_new_tokens = int(max_new_tokens)

        try:
            import torch
            from transformers import (
                AutoProcessor,
                Qwen2_5_VLForConditionalGeneration,
            )
            from qwen_vl_utils import process_vision_info
        except ImportError as exc:
            raise RuntimeError(
                "Missing Qwen runtime dependencies. Install transformers, "
                "torch, pillow and qwen-vl-utils in the qwen312 environment."
            ) from exc

        self._torch = torch
        self._process_vision_info = process_vision_info

        self.processor = AutoProcessor.from_pretrained(
            self.model_path,
            trust_remote_code=True,
        )

        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            self.model_path,
            torch_dtype="auto",
            device_map="auto",
            trust_remote_code=True,
        )

        self.model.eval()

    def generate(
        self,
        prompt: str,
        *,
        image_path: str | None = None,
    ) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")

        content: list[dict[str, Any]] = []

        if image_path is not None:
            image = Path(image_path)

            if not image.is_file():
                raise FileNotFoundError(
                    f"runtime image not found: {image}"
                )

            content.append({
                "type": "image",
                "image": str(image.resolve()),
            })

        content.append({
            "type": "text",
            "text": prompt,
        })

        messages = [{
            "role": "user",
            "content": content,
        }]

        chat_text = self.processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        image_inputs, video_inputs = self._process_vision_info(
            messages
        )

        processor_kwargs: dict[str, Any] = {
            "text": [chat_text],
            "padding": True,
            "return_tensors": "pt",
        }

        if image_inputs:
            processor_kwargs["images"] = image_inputs

        if video_inputs:
            processor_kwargs["videos"] = video_inputs

        inputs = self.processor(**processor_kwargs)

        device = next(self.model.parameters()).device
        inputs = inputs.to(device)

        with self._torch.inference_mode():
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                use_cache=True,
            )

        trimmed_ids = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(
                inputs.input_ids,
                generated_ids,
            )
        ]

        outputs = self.processor.batch_decode(
            trimmed_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )

        if not outputs:
            raise RuntimeError("Qwen returned no decoded output")

        return outputs[0].strip()
