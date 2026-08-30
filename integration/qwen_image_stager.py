"""Stage CARLA RGB snapshots from A's slow worker, never the control thread."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import io
from pathlib import Path, PurePosixPath
from threading import Lock
from typing import Any

from .rgb_detector import carla_rgb_array


class QwenImageStager:
    def __init__(self, image_root: str | Path, *, ref_prefix: str = "artifacts/qwen_live") -> None:
        try:
            from PIL import Image, ImageOps
        except ImportError as error:  # pragma: no cover - deployment dependency
            raise RuntimeError("Pillow is required to stage Qwen RGB images") from error
        self.image_root = Path(image_root).expanduser().resolve()
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
        self._captures: dict[str, tuple[Any, str, bool]] = {}

    def stage(self, command_id: str, measurement: Any, *, frame_id: int) -> str:
        if type(command_id) is not str or not command_id:
            raise ValueError("command_id must be a non-empty string")
        if type(frame_id) is not int or frame_id < 0:
            raise ValueError("frame_id must be a non-negative integer")
        digest = hashlib.sha256(command_id.encode("utf-8")).hexdigest()[:16]
        reference = str(self.ref_prefix / f"frame_{frame_id:08d}_{digest}.jpg")
        with self._lock:
            self._captures[command_id] = (measurement, reference, False)
        return reference

    def stage_multiview(
        self,
        command_id: str,
        measurements: Mapping[str, Any],
        *,
        frame_id: int,
    ) -> str:
        """Stage an exact-frame four-camera montage for one Qwen request.

        The fixed layout is front/left on the first row and right/rear on the
        second row.  It keeps the frozen single-image model contract while
        ensuring the official S2/S3 Qwen request actually contains all four
        camera views instead of merely logging their presence.
        """
        if type(command_id) is not str or not command_id:
            raise ValueError("command_id must be a non-empty string")
        if type(frame_id) is not int or frame_id < 0:
            raise ValueError("frame_id must be a non-negative integer")
        required = ("rgb_front", "rgb_left", "rgb_right", "rgb_rear")
        missing = [sensor_id for sensor_id in required if sensor_id not in measurements]
        if missing:
            raise ValueError(f"multiview measurements missing sensors: {missing}")
        digest = hashlib.sha256(command_id.encode("utf-8")).hexdigest()[:16]
        reference = str(
            self.ref_prefix / f"multiview_frame_{frame_id:08d}_{digest}.jpg"
        )
        capture = {sensor_id: measurements[sensor_id] for sensor_id in required}
        with self._lock:
            self._captures[command_id] = (capture, reference, True)
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
        measurement, reference, multiview = staged
        target = (self.image_root / Path(reference)).resolve()
        try:
            target.relative_to(self.image_root)
        except ValueError as error:
            raise ValueError("staged Qwen image escapes image_root") from error
        target.parent.mkdir(parents=True, exist_ok=True)
        Image = self._image_module
        ImageOps = self._image_ops
        if multiview:
            assert isinstance(measurement, Mapping)
            image = Image.new("RGB", (224, 224), (0, 0, 0))
            placements = (
                ("rgb_front", (0, 0)),
                ("rgb_left", (112, 0)),
                ("rgb_right", (0, 112)),
                ("rgb_rear", (112, 112)),
            )
            for sensor_id, position in placements:
                tile = ImageOps.fit(
                    self._measurement_image(measurement[sensor_id]),
                    (112, 112),
                    method=Image.Resampling.BILINEAR,
                )
                image.paste(tile, position)
        else:
            image = ImageOps.pad(
                self._measurement_image(measurement),
                (224, 224),
                # The model receives only a 224 px / 64-token visual budget.  A
                # bilinear downsample preserves that information while avoiding
                # the unnecessary high-order LANCZOS cost on the latency path.
                method=Image.Resampling.BILINEAR,
                color=(0, 0, 0),
            )
        image.save(target, format="JPEG", quality=75)
        payload = dict(request)
        payload["rgb_ref"] = reference
        return payload

    def _measurement_image(self, measurement: Any) -> Any:
        Image = self._image_module
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
            return Image.frombuffer(
                "RGBA", (width, height), raw, "raw", "BGRA", 0, 1,
            ).convert("RGB")
        return Image.fromarray(carla_rgb_array(measurement), mode="RGB")


__all__ = ["QwenImageStager"]
