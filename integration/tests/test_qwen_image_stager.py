from __future__ import annotations

import base64
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from integration.qwen_image_stager import QwenImageStager


def test_stager_writes_rgb_only_when_slow_worker_prepares_request(tmp_path) -> None:
    stager = QwenImageStager(tmp_path, ref_prefix="frames")
    measurement = SimpleNamespace(
        rgb_array=np.full((4, 6, 3), 127, dtype=np.uint8),
    )
    reference = stager.stage("voice-1", measurement, frame_id=12)
    target = tmp_path / reference
    assert not target.exists()

    prepared = stager.prepare_request({
        "command_id": "voice-1", "rgb_ref": reference,
    })

    assert prepared["rgb_ref"] == reference
    assert target.is_file()
    assert target.suffix == ".jpg"
    with Image.open(target) as image:
        assert image.size == (224, 224)
        assert image.format == "JPEG"


def test_stager_rejects_path_escape_and_discard_skips_write(tmp_path) -> None:
    with pytest.raises(ValueError, match="safe relative"):
        QwenImageStager(tmp_path, ref_prefix="../escape")
    stager = QwenImageStager(tmp_path)
    measurement = SimpleNamespace(rgb_array=np.zeros((2, 2, 3), dtype=np.uint8))
    reference = stager.stage("voice-2", measurement, frame_id=1)
    stager.discard("voice-2")
    prepared = stager.prepare_request({"command_id": "voice-2", "rgb_ref": reference})
    assert prepared["rgb_ref"] == reference
    assert not (tmp_path / reference).exists()


def test_stager_decodes_native_carla_bgra_without_swapping_colors(tmp_path) -> None:
    stager = QwenImageStager(tmp_path, ref_prefix="frames")
    # Opaque red in CARLA's native BGRA byte order.
    pixel = bytes((0, 0, 255, 255))
    measurement = SimpleNamespace(raw_data=pixel * 24, width=6, height=4)
    reference = stager.stage("voice-bgra", measurement, frame_id=13)

    prepared = stager.prepare_request({"command_id": "voice-bgra"})

    assert prepared["rgb_ref"] == reference
    with Image.open(tmp_path / reference) as image:
        red, green, blue = image.convert("RGB").getpixel((112, 112))
    assert red > 240
    assert green < 15
    assert blue < 15


def test_stager_can_inline_jpeg_for_remote_host(tmp_path) -> None:
    stager = QwenImageStager(tmp_path, ref_prefix="frames", transport="inline")
    measurement = SimpleNamespace(
        raw_data=bytes((0, 0, 255, 255)) * 4, width=2, height=2,
    )
    reference = stager.stage("voice-inline", measurement, frame_id=9)

    prepared = stager.prepare_request({"command_id": "voice-inline"})

    prefix = "data:image/jpeg;base64,"
    assert prepared["rgb_ref"].startswith(prefix)
    assert base64.b64decode(prepared["rgb_ref"][len(prefix):]).startswith(b"\xff\xd8")
    assert (tmp_path / reference).is_file()
