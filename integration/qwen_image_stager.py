"""Stage CARLA RGB snapshots from A's slow worker, never the control thread."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from pathlib import Path, PurePosixPath
from threading import Lock
from typing import Any

from .rgb_detector import carla_rgb_array


class QwenImageStager:
    def __init__(self, image_root: str | Path, *, ref_prefix: str = "artifacts/qwen_live") -> None:
        self.image_root = Path(image_root).expanduser().resolve()
        prefix = PurePosixPath(str(ref_prefix).replace("\\", "/"))
        if prefix.is_absolute() or ".." in prefix.parts:
            raise ValueError("ref_prefix must be a safe relative path")
        self.ref_prefix = prefix
        self._lock = Lock()
        self._captures: dict[str, tuple[Any, str]] = {}

    def stage(self, command_id: str, measurement: Any, *, frame_id: int) -> str:
        if type(command_id) is not str or not command_id:
            raise ValueError("command_id must be a non-empty string")
        if type(frame_id) is not int or frame_id < 0:
            raise ValueError("frame_id must be a non-negative integer")
        digest = hashlib.sha256(command_id.encode("utf-8")).hexdigest()[:16]
        reference = str(self.ref_prefix / f"frame_{frame_id:08d}_{digest}.png")
        with self._lock:
            self._captures[command_id] = (measurement, reference)
        return reference

    def discard(self, command_id: str) -> None:
        with self._lock:
            self._captures.pop(command_id, None)

    def prepare_request(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        command_id = str(request.get("command_id", ""))
        with self._lock:
            staged = self._captures.pop(command_id, None)
        if staged is None:
            return dict(request)
        measurement, reference = staged
        target = (self.image_root / Path(reference)).resolve()
        try:
            target.relative_to(self.image_root)
        except ValueError as error:
            raise ValueError("staged Qwen image escapes image_root") from error
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            from PIL import Image
        except ImportError as error:  # pragma: no cover - deployment dependency
            raise RuntimeError("Pillow is required to stage Qwen RGB images") from error
        Image.fromarray(carla_rgb_array(measurement), mode="RGB").save(target, format="PNG")
        payload = dict(request)
        payload["rgb_ref"] = reference
        return payload


__all__ = ["QwenImageStager"]
