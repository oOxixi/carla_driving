from __future__ import annotations

from dataclasses import dataclass
from queue import Empty, Full, Queue
from typing import Optional
import threading
import traceback

import numpy as np


@dataclass(frozen=True)
class RGBFrame:
    """One CARLA RGB camera frame."""

    frame: int
    sim_time_s: float
    image_bgr: np.ndarray
    sensor_transform: object


class FrontRGBCamera:
    """Front RGB camera with a bounded frame queue.

    Important lifecycle rules:
    1. stop listening before actor destruction;
    2. do not keep CARLA Image objects in the queue;
    3. copy raw pixels inside the callback;
    4. tolerate callbacks arriving during shutdown.
    """

    def __init__(
        self,
        world,
        vehicle,
        width: int = 1280,
        height: int = 720,
        fov_deg: float = 90.0,
        sensor_tick: float = 0.05,
        x_m: float = 1.5,
        z_m: float = 2.4,
        pitch_deg: float = -5.0,
        queue_size: int = 16,
    ) -> None:
        import carla

        self.width = int(width)
        self.height = int(height)
        self.fov_deg = float(fov_deg)

        self._queue: Queue[RGBFrame] = Queue(maxsize=max(2, int(queue_size)))
        self._closed = threading.Event()
        self._callback_error: Optional[str] = None
        self.actor = None

        bp = world.get_blueprint_library().find("sensor.camera.rgb")
        bp.set_attribute("image_size_x", str(self.width))
        bp.set_attribute("image_size_y", str(self.height))
        bp.set_attribute("fov", str(self.fov_deg))

        # In synchronous mode, camera should normally produce one image per tick.
        # Setting sensor_tick to zero avoids floating-point cadence mismatch.
        if bp.has_attribute("sensor_tick"):
            bp.set_attribute("sensor_tick", "0.0")

        transform = carla.Transform(
            carla.Location(x=float(x_m), y=0.0, z=float(z_m)),
            carla.Rotation(pitch=float(pitch_deg), yaw=0.0, roll=0.0),
        )

        self.actor = world.spawn_actor(
            bp,
            transform,
            attach_to=vehicle,
            attachment_type=carla.AttachmentType.Rigid,
        )
        self.actor.listen(self._on_image)

    @property
    def callback_error(self) -> Optional[str]:
        return self._callback_error

    def _on_image(self, image) -> None:
        if self._closed.is_set():
            return

        try:
            array = np.frombuffer(image.raw_data, dtype=np.uint8)
            expected = int(image.width) * int(image.height) * 4

            if array.size != expected:
                self._callback_error = (
                    f"Unexpected RGB buffer size: got={array.size}, "
                    f"expected={expected}"
                )
                return

            array = array.reshape((int(image.height), int(image.width), 4))

            # CARLA gives BGRA. Keep the first three channels as BGR for OpenCV.
            bgr = np.ascontiguousarray(array[:, :, :3])

            item = RGBFrame(
                frame=int(image.frame),
                sim_time_s=float(image.timestamp),
                image_bgr=bgr,
                sensor_transform=image.transform,
            )

            while not self._closed.is_set():
                try:
                    self._queue.put_nowait(item)
                    break
                except Full:
                    try:
                        self._queue.get_nowait()
                    except Empty:
                        break

        except Exception:
            self._callback_error = traceback.format_exc()

    def get(self, timeout_s: float = 5.0) -> RGBFrame:
        """Return the next available RGB frame."""

        if self._closed.is_set():
            raise RuntimeError("RGB camera has already been closed")

        try:
            return self._queue.get(timeout=float(timeout_s))
        except Empty as exc:
            detail = ""
            if self._callback_error:
                detail = f"\nCamera callback error:\n{self._callback_error}"
            raise TimeoutError(
                f"No RGB frame received within {float(timeout_s):.1f}s."
                f"{detail}"
            ) from exc

    def get_for_frame(
        self,
        expected_frame: int,
        timeout_s: float = 5.0,
        max_frame_lag: int = 2,
    ) -> RGBFrame:
        """Return a frame matching or closely following the CARLA world frame."""

        expected_frame = int(expected_frame)
        max_frame_lag = max(0, int(max_frame_lag))

        while True:
            item = self.get(timeout_s=timeout_s)

            if item.frame < expected_frame:
                continue

            if item.frame > expected_frame + max_frame_lag:
                raise RuntimeError(
                    "RGB/world frame mismatch: "
                    f"expected={expected_frame}, received={item.frame}"
                )

            return item

    def drain(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except Empty:
                return

    def stop(self) -> None:
        """Stop callback delivery without destroying the CARLA actor."""

        if self._closed.is_set():
            return

        self._closed.set()

        actor = self.actor
        if actor is not None:
            try:
                if actor.is_alive:
                    actor.stop()
            except Exception:
                pass

        self.drain()

    def destroy(self) -> None:
        """Stop and destroy the sensor safely."""

        self.stop()

        actor = self.actor
        self.actor = None

        if actor is not None:
            try:
                if actor.is_alive:
                    actor.destroy()
            except Exception:
                # Cleanup must never mask the original runtime exception.
                pass
