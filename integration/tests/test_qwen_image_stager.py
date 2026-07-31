from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

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
