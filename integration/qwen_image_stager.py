"""Stage CARLA RGB snapshots from A's slow worker, never the control thread."""

from __future__ import annotations

from collections.abc import Mapping
import base64
import hashlib
import io
from pathlib import Path, PurePosixPath
from threading import Lock
from typing import Any

from .rgb_detector import carla_rgb_array


class QwenImageStager:
    def __init__(
        self,
        image_root: str | Path,
        *,
        ref_prefix: str = "artifacts/qwen_live",
        transport: str = "shared",
    ) -> None:
        try:
            from PIL import Image, ImageOps
        except ImportError as error:  # pragma: no cover - deployment dependency
            raise RuntimeError("Pillow is required to stage Qwen RGB images") from error
        self.image_root = Path(image_root).expanduser().resolve()
        if transport not in {"shared", "inline"}:
            raise ValueError("transport must be shared or inline")
        self.transport = transport
        prefix = PurePosixPath(str(ref_prefix).replace("\\", "/"))
        if prefix.is_absolute() or ".." in prefix.parts:
            raise ValueError("ref_prefix must be a safe relative path")
        self.ref_prefix = prefix
        # Import and initialize Pillow before the first measured request.  The
        # acceptance suite starts one process per scenario; leaving this import
        # on the request path adds an otherwise repeatable ~18 ms cold start.
        self._image_module = Image
        self._image_ops = ImageOps
        Image.init()
        jpeg_probe = io.BytesIO()
        Image.new("RGB", (1, 1)).save(jpeg_probe, format="JPEG", quality=75)
        self._lock = Lock()
        self._captures: dict[str, tuple[Any, str]] = {}

    def stage(self, command_id: str, measurement: Any, *, frame_id: int) -> str:
        if type(command_id) is not str or not command_id:
            raise ValueError("command_id must be a non-empty string")
        if type(frame_id) is not int or frame_id < 0:
            raise ValueError("frame_id must be a non-negative integer")
        digest = hashlib.sha256(command_id.encode("utf-8")).hexdigest()[:16]
        reference = str(self.ref_prefix / f"frame_{frame_id:08d}_{digest}.jpg")
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
        Image = self._image_module
        ImageOps = self._image_ops
        raw = getattr(measurement, "raw_data", None)
        width = getattr(measurement, "width", None)
        height = getattr(measurement, "height", None)
        if (
            raw is not None
            and type(width) is int and width > 0
            and type(height) is int and height > 0
        ):
            # Decode CARLA's native BGRA buffer directly.  Building a full-size
            # RGB NumPy copy first costs several milliseconds and carries no
            # information into the fixed 224 px model input.
            image = Image.frombuffer(
                "RGBA", (width, height), raw, "raw", "BGRA", 0, 1,
            ).convert("RGB")
        else:
            image = Image.fromarray(carla_rgb_array(measurement), mode="RGB")
        image = ImageOps.pad(
            image,
            (224, 224),
            # The model receives only a 224 px / 64-token visual budget.  A
            # bilinear downsample preserves that information while avoiding
            # the unnecessary high-order LANCZOS cost on the latency path.
            method=Image.Resampling.BILINEAR,
            color=(0, 0, 0),
        )
        image.save(target, format="JPEG", quality=75)
        payload = dict(request)
        payload["rgb_ref"] = (
            "data:image/jpeg;base64," + base64.b64encode(target.read_bytes()).decode("ascii")
            if self.transport == "inline"
            else reference
        )
        return payload


__all__ = ["QwenImageStager"]
