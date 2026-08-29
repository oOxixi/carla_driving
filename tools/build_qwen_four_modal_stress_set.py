"""Build an auditable four-modal Qwen stress set from real CARLA captures.

RGB/LiDAR inputs remain traceable to the source capture. Exposure, motion blur,
and partial occlusion variants are deterministic synthetic augmentations and
are labelled as such. Detector-error cases mutate only the structured detector
view; they never alter the CARLA ground-truth annotation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


VARIANTS = (
    "baseline",
    "exposure_low",
    "exposure_high",
    "motion_blur",
    "partial_occlusion",
    "detector_false_positive",
    "detector_miss",
    "detector_bbox_shift",
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"{path} must contain JSON objects")
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _split(scene_id: str) -> str:
    bucket = int.from_bytes(
        hashlib.sha256(scene_id.encode("utf-8")).digest()[:8],
        "big",
    ) % 100
    if bucket < 70:
        return "train"
    if bucket < 85:
        return "val"
    return "test"


def _target_bbox(case: dict[str, Any]) -> list[float] | None:
    target = case.get("expected", {}).get("target_track_id")
    for item in case.get("perception", {}).get("detected_objects", []):
        if item.get("track_id") == target:
            bbox = item.get("bbox_xyxy_norm")
            if (
                isinstance(bbox, list)
                and len(bbox) == 4
                and all(isinstance(value, (int, float)) for value in bbox)
            ):
                return [float(value) for value in bbox]
    return None


def _repair_legacy_target_semantics(
    case: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Repair the known adjacent-vs-far pedestrian label bug audibly.

    Older CARLA collections fell back to a far-ahead waypoint when Town03 had
    no usable adjacent lane, but still described every non-left pedestrian as
    right-adjacent.  Preserve the captured target and relation, and correct the
    language label instead of inventing an actor that is absent from the frame.
    """
    repaired = json.loads(json.dumps(case))
    expected = repaired.get("expected", {})
    target_id = expected.get("target_track_id")
    target = next(
        (
            item
            for item in repaired.get("perception", {}).get(
                "detected_objects", []
            )
            if item.get("track_id") == target_id
        ),
        None,
    )
    if not isinstance(target, dict) or target.get("class") != "pedestrian":
        return repaired, None
    relation = str(target.get("relation", ""))
    command = str(repaired.get("voice_command", ""))
    if "相邻车道" not in command or not relation.startswith("far_ahead"):
        return repaired, None
    phrase = (
        "被前车部分遮挡的较远行人"
        if "occluded" in relation
        else "前方较远的行人"
    )
    corrected_command = f"减速并避让{phrase}"
    repaired["voice_command"] = corrected_command
    repaired.setdefault("expected", {})["actions"] = ["SLOW_DOWN"]
    return repaired, {
        "kind": "legacy_adjacent_pedestrian_relation_repair",
        "original_voice_command": command,
        "corrected_voice_command": corrected_command,
        "target_track_id": target_id,
        "target_relation": relation,
    }


def _transform_image(
    source: Path,
    destination: Path,
    variant: str,
    *,
    bbox: list[float] | None,
) -> dict[str, Any]:
    with Image.open(source) as opened:
        image = opened.convert("RGB")
        original_size = list(image.size)
        if variant == "exposure_low":
            image = ImageEnhance.Brightness(image).enhance(0.42)
        elif variant == "exposure_high":
            image = ImageEnhance.Brightness(image).enhance(1.75)
            image = ImageEnhance.Contrast(image).enhance(0.82)
        elif variant == "motion_blur":
            kernel = [0.0] * 25
            for index in range(10, 15):
                kernel[index] = 0.2
            image = image.filter(
                ImageFilter.Kernel((5, 5), kernel, scale=1.0),
            )
        elif variant == "partial_occlusion":
            if bbox is None:
                raise ValueError("partial_occlusion requires a target bbox")
            width, height = image.size
            left, top, right, bottom = bbox
            x0 = int(width * (left + (right - left) * 0.42))
            y0 = int(height * top)
            x1 = int(width * right)
            y1 = int(height * bottom)
            ImageDraw.Draw(image).rectangle(
                (x0, y0, x1, y1),
                fill=(74, 78, 83),
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, format="PNG", optimize=True)
    return {
        "kind": variant,
        "synthetic": variant != "baseline",
        "source_rgb_sha256": _sha256(source),
        "output_rgb_sha256": _sha256(destination),
        "image_size": original_size,
    }


def _mutate_detector(
    case: dict[str, Any],
    variant: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    perception = json.loads(json.dumps(case.get("perception", {})))
    expected = json.loads(json.dumps(case.get("expected", {})))
    objects = perception.setdefault("detected_objects", [])
    target = expected.get("target_track_id")
    if variant == "detector_false_positive":
        objects.append({
            "track_id": f"ghost_{case['case_id']}",
            "class": "vehicle",
            "relation": "center_ahead",
            "distance_m": 8.0,
            "confidence": 0.31,
            "bbox_xyxy_norm": [0.44, 0.42, 0.57, 0.72],
            "source": "synthetic_detector_false_positive",
        })
    elif variant == "detector_miss":
        target_object = next(
            (item for item in objects if item.get("track_id") == target),
            None,
        )
        if target_object is None:
            raise ValueError("detector_miss target is absent before mutation")
        target_class = target_object.get("class")
        target_relation = str(target_object.get("relation", ""))

        def same_explicit_target(item: dict[str, Any]) -> bool:
            if item.get("class") != target_class:
                return False
            relation = str(item.get("relation", ""))
            if target_relation == "center_ahead":
                return relation == "center_ahead"
            if "left_adjacent" in target_relation:
                return "left_adjacent" in relation
            if "right_adjacent" in target_relation:
                return "right_adjacent" in relation
            if target_relation.startswith("far_ahead"):
                if "occluded" in target_relation:
                    return "occluded" in relation
                return relation.startswith("far_ahead")
            return item.get("track_id") == target

        removed_ids = [
            str(item.get("track_id"))
            for item in objects
            if same_explicit_target(item)
        ]
        perception["detected_objects"] = [
            item for item in objects if not same_explicit_target(item)
        ]
        perception["detector_fault"] = {
            "kind": "miss",
            "removed_track_ids": removed_ids,
            "target_class": target_class,
            "target_relation": target_relation,
        }
        expected = {
            "actions": ["STOP"],
            "requires_confirmation": True,
            "target_track_id": None,
            "safety_expectation": "fail_closed_on_missing_target",
        }
    elif variant == "detector_bbox_shift":
        for item in objects:
            if item.get("track_id") != target:
                continue
            bbox = item.get("bbox_xyxy_norm")
            if isinstance(bbox, list) and len(bbox) == 4:
                item["bbox_xyxy_norm"] = [
                    round(min(1.0, max(0.0, float(value) + offset)), 6)
                    for value, offset in zip(
                        bbox,
                        (0.08, -0.03, 0.08, -0.03),
                    )
                ]
                item["source"] = "synthetic_detector_bbox_shift"
    return perception, expected


def build(
    collection_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    collection_dir = collection_dir.resolve()
    output_dir = output_dir.resolve()
    scenes = _read_jsonl(collection_dir / "scenes.jsonl")
    cases = _read_jsonl(collection_dir / "cases.jsonl")
    scenes_by_rgb = {scene["rgb_ref"]: scene for scene in scenes}
    output_images = output_dir / "images"
    output_lidar = output_dir / "lidar"
    output_images.mkdir(parents=True, exist_ok=True)
    output_lidar.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    semantic_repairs: list[dict[str, Any]] = []

    for source_case in cases:
        case, semantic_repair = _repair_legacy_target_semantics(source_case)
        if semantic_repair is not None:
            semantic_repairs.append({
                "source_case_id": source_case["case_id"],
                **semantic_repair,
            })
        source_scene = scenes_by_rgb.get(case.get("rgb_ref"))
        if source_scene is None:
            raise ValueError(f"case has no matching scene: {case['case_id']}")
        source_image = collection_dir / source_scene["rgb_ref"]
        source_lidar_ref = source_scene.get("lidar_ref")
        if not source_lidar_ref:
            raise ValueError(
                f"scene {source_scene['scene_id']} has no raw LiDAR reference"
            )
        source_lidar = collection_dir / source_lidar_ref
        if not source_image.is_file() or not source_lidar.is_file():
            raise FileNotFoundError("source RGB/LiDAR file is missing")
        lidar_name = f"{source_scene['scene_id']}.npy"
        lidar_destination = output_lidar / lidar_name
        if not lidar_destination.exists():
            shutil.copy2(source_lidar, lidar_destination)

        for variant in VARIANTS:
            variant_id = f"{case['case_id']}__{variant}"
            image_destination = output_images / f"{variant_id}.png"
            image_variant = (
                variant
                if variant in {
                    "exposure_low",
                    "exposure_high",
                    "motion_blur",
                    "partial_occlusion",
                }
                else "baseline"
            )
            augmentation = _transform_image(
                source_image,
                image_destination,
                image_variant,
                bbox=_target_bbox(case),
            )
            perception, expected = _mutate_detector(case, variant)
            lidar_summary = perception.setdefault("lidar_summary", {})
            lidar_summary.update({
                "valid": True,
                "point_count": source_scene["lidar_point_count"],
                "raw_ref": f"lidar/{lidar_name}",
                "raw_sha256": _sha256(lidar_destination),
                "source": "raw_carla_lidar",
            })
            scene_state = {
                "map": source_scene["map"],
                "weather_profile": source_scene["weather_profile"],
                "ego_speed_mps": float(
                    case.get("scene_state", {}).get("ego_speed_mps", 3.0)
                ),
                "augmentation": {
                    **augmentation,
                    "detector_variant": (
                        variant if variant.startswith("detector_") else "none"
                    ),
                },
                "modalities": {
                    "voice": "audio_to_sensevoice",
                    "rgb": "real_carla_or_labelled_augmentation",
                    "lidar": "raw_carla_lidar_plus_structured_summary",
                    "ego_state": "structured_vehicle_state",
                },
            }
            rows.append({
                "schema_version": "1.0",
                "case_id": variant_id,
                "source_scene_id": source_scene["scene_id"],
                "split": _split(source_scene["scene_id"]),
                "category": variant,
                "rgb_ref": f"images/{variant_id}.png",
                "lidar_ref": f"lidar/{lidar_name}",
                "audio_ref": None,
                "expected_transcript": case["voice_command"],
                "voice_command": case["voice_command"],
                "scene_state": scene_state,
                "perception": perception,
                "safety_state": {
                    "input_confidence": 1.0,
                    "recommended_action": (
                        "STOP" if variant == "detector_miss" else "KEEP_SPEED"
                    ),
                    "reason": (
                        "detector_target_missing"
                        if variant == "detector_miss"
                        else "no_immediate_hazard"
                    ),
                    "visual_valid": True,
                    "lidar_valid": True,
                },
                "expected": expected,
                "provenance": {
                    "source": "real_carla_0.9.16_capture",
                    "augmentation": augmentation,
                    "semantic_repair": semantic_repair,
                    "detector_mutation": (
                        variant if variant.startswith("detector_") else "none"
                    ),
                },
            })

    _write_jsonl(output_dir / "cases.jsonl", rows)
    report = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_collection": str(collection_dir),
        "source_scene_count": len(scenes),
        "source_case_count": len(cases),
        "case_count": len(rows),
        "semantic_source_repairs": semantic_repairs,
        "semantic_source_repair_count": len(semantic_repairs),
        "generated_cases_from_repaired_sources": (
            len(semantic_repairs) * len(VARIANTS)
        ),
        "variant_counts": dict(Counter(row["category"] for row in rows)),
        "split_counts": dict(Counter(row["split"] for row in rows)),
        "all_cases_have_four_modal_contract": all(
            set(row["scene_state"]["modalities"])
            == {"voice", "rgb", "lidar", "ego_state"}
            for row in rows
        ),
        "all_lidar_files_hashed": all(
            bool(row["perception"]["lidar_summary"]["raw_sha256"])
            for row in rows
        ),
        "limitations": [
            "Exposure, motion blur and partial occlusion are deterministic "
            "augmentations of real CARLA RGB frames.",
            "Detector-error records are structured fault-injection cases.",
            "Audio references are populated by the separate TTS/audio capture step "
            "before full-chain evaluation.",
        ],
    }
    (output_dir / "dataset_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    report = build(args.collection_dir, args.output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
