from __future__ import annotations

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


def test_stager_accepts_linux_carla_writable_memoryview(tmp_path) -> None:
    stager = QwenImageStager(tmp_path, ref_prefix="frames")
    # The Linux CARLA 0.9.16 binding exposes Image.raw_data as a writable
    # memoryview, while Pillow's raw decoder only accepts a read-only buffer.
    pixel = bytes((0, 0, 255, 255))
    measurement = SimpleNamespace(
        raw_data=memoryview(bytearray(pixel * 24)),
        width=6,
        height=4,
    )
    reference = stager.stage("voice-linux-bgra", measurement, frame_id=14)

    prepared = stager.prepare_request({"command_id": "voice-linux-bgra"})

    assert prepared["rgb_ref"] == reference
    with Image.open(tmp_path / reference) as image:
        red, green, blue = image.convert("RGB").getpixel((112, 112))
    assert red > 240
    assert green < 15
    assert blue < 15


def test_stager_builds_exact_frame_four_camera_montage(tmp_path) -> None:
    stager = QwenImageStager(tmp_path, ref_prefix="frames")
    colors = {
        "rgb_front": (255, 0, 0),
        "rgb_left": (0, 255, 0),
        "rgb_right": (0, 0, 255),
        "rgb_rear": (255, 255, 0),
    }
    measurements = {
        sensor_id: SimpleNamespace(
            rgb_array=np.full((8, 12, 3), color, dtype=np.uint8),
            frame=42,
        )
        for sensor_id, color in colors.items()
    }

    reference = stager.stage_multiview("voice-multi", measurements, frame_id=42)
    prepared = stager.prepare_request({"command_id": "voice-multi"})

    assert prepared["rgb_ref"] == reference
    assert "multiview" in reference
    with Image.open(tmp_path / reference) as image:
        image = image.convert("RGB")
        samples = (
            image.getpixel((56, 56)),
            image.getpixel((168, 56)),
            image.getpixel((56, 168)),
            image.getpixel((168, 168)),
        )
    assert samples[0][0] > 240 and samples[0][1] < 15 and samples[0][2] < 15
    assert samples[1][1] > 240 and samples[1][0] < 15 and samples[1][2] < 15
    assert samples[2][2] > 240 and samples[2][0] < 15 and samples[2][1] < 15
    assert samples[3][0] > 240 and samples[3][1] > 240 and samples[3][2] < 15

def test_target_box_is_transformed_to_letterboxed_model_image(tmp_path):
    stager=QwenImageStager(tmp_path,ref_prefix='frames')
    measurement=SimpleNamespace(rgb_array=np.zeros((200,400,3),dtype=np.uint8))
    reference=stager.stage('box-transform',measurement,frame_id=20)
    stager.prepare_request({'command_id':'box-transform','target_grounding':{'visual_candidates':[
        {'target_id':'V1','label':'T1','bbox_xyxy_norm':[.25,.25,.75,.75]}]}})
    with Image.open(tmp_path/reference) as image:
        pixels=np.asarray(image.convert('RGB')).astype(int)
    # The 16-pixel header and aspect-ratio padding map x=.25 to 56, y=.25 to 92.
    patch=pixels[90:95,54:60]
    assert np.any((patch[:,:,1]>100)&(patch[:,:,1]>patch[:,:,0]+50)&(patch[:,:,1]>patch[:,:,2]+50))
    # Incorrect untransformed y=.25 would be at the top of the black padding.
    assert pixels[56,56].max()<20

def test_labels_use_separate_header_and_do_not_cover_target_interiors(tmp_path):
    stager=QwenImageStager(tmp_path,ref_prefix='frames')
    rgb=np.full((224,224,3),180,dtype=np.uint8)
    reference=stager.stage('two-objects',SimpleNamespace(rgb_array=rgb),frame_id=2)
    stager.prepare_request({'command_id':'two-objects','target_grounding':{'visual_candidates':[
        {'target_id':'V1','label':'T1','bbox_xyxy_norm':[.40,.40,.48,.50]},
        {'target_id':'V2','label':'T2','bbox_xyxy_norm':[.50,.40,.58,.50]}]}})
    with Image.open(tmp_path/reference) as image:
        pixels=np.asarray(image.convert('RGB')).astype(int)
    # The top header has two separate coloured labels; neither is on the scene.
    assert pixels[:16,:56].max()>100 and pixels[:16,56:112].max()>100
    # Centres of both nearby boxes retain the original grey scene pixels.
    for x in (99,121):
        r,g,b=pixels[110,x]
        assert abs(r-g)<20 and abs(g-b)<20 and min(r,g,b)>150
