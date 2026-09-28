"""Build deterministic B1 Calibration v1 from D2 v1.1 reserved candidates.

This builder does NOT mutate the immutable D2 v1.1 release.

Selection:
    source x scenario_family x authoritative training_role
    proportional largest-remainder allocation
    deterministic SHA256 ranking inside each stratum

Calibration is a PTQ calibration asset, not Frozen Test.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

SOURCE_RELEASE = (
    ROOT / "challenge/dataset/releases/d2_v1_1"
)

OUT = (
    ROOT / "challenge/dataset/releases/calibration_v1"
)

RESERVED = (
    SOURCE_RELEASE / "reserved_test_candidates.jsonl"
)

ASSIGNMENTS = (
    SOURCE_RELEASE / "source_split_assignments.jsonl"
)

RGB_MAPPING = (
    SOURCE_RELEASE / "rgb_mapping.json"
)

SOURCE_RELEASE_MANIFEST = (
    SOURCE_RELEASE / "release_manifest.json"
)

TARGET_COUNT = 300

SELECTION_SALT = (
    "b1-calibration-v1/"
    "source-family-role/"
    "sha256-rank-v1"
)

DATASET_VERSION = "b1_calibration_v1"


def canonical_text_sha256(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def raw_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    with path.open(encoding="utf-8") as f:
        for line_no, raw in enumerate(f, 1):
            if not raw.strip():
                continue

            row = json.loads(raw)
            row["_input_line_no"] = line_no
            rows.append(row)

    return rows


def write_json(
    path: Path,
    obj: Any,
) -> None:
    path.write_text(
        json.dumps(
            obj,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def write_jsonl(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as f:
        for row in rows:
            f.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )


def stable_rank(sample_id: str) -> str:
    payload = (
        f"{SELECTION_SALT}\t{sample_id}"
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def largest_remainder(
    counts: dict[tuple[str, str, str], int],
    target: int,
) -> dict[tuple[str, str, str], int]:
    total = sum(counts.values())

    if target > total:
        raise RuntimeError(
            "target exceeds available pool"
        )

    quotas: dict[
        tuple[str, str, str],
        int,
    ] = {}

    remainders: list[
        tuple[
            float,
            tuple[str, str, str],
        ]
    ] = []

    allocated = 0

    for key in sorted(counts):
        exact = counts[key] * target / total
        base = int(exact)

        quotas[key] = base
        allocated += base

        remainders.append(
            (
                exact - base,
                key,
            )
        )

    remaining = target - allocated

    remainders.sort(
        key=lambda x: (
            -x[0],
            x[1],
        )
    )

    for _, key in remainders[:remaining]:
        quotas[key] += 1

    if sum(quotas.values()) != target:
        raise RuntimeError(
            "quota allocation failed"
        )

    for key, quota in quotas.items():
        if quota > counts[key]:
            raise RuntimeError(
                f"quota exceeds stratum: "
                f"{key}: {quota}>{counts[key]}"
            )

    return quotas


def main() -> None:
    if OUT.exists():
        raise RuntimeError(
            f"refusing to overwrite existing "
            f"release: {OUT}"
        )

    required = (
        RESERVED,
        ASSIGNMENTS,
        RGB_MAPPING,
        SOURCE_RELEASE_MANIFEST,
    )

    for path in required:
        if not path.is_file():
            raise RuntimeError(
                f"missing source file: {path}"
            )

    reserved = load_jsonl(RESERVED)
    assignments = load_jsonl(ASSIGNMENTS)

    if len(reserved) != 540:
        raise RuntimeError(
            f"expected 540 reserved rows, "
            f"got {len(reserved)}"
        )

    assignment_by_id = {}

    for row in assignments:
        sid = str(
            row.get("sample_id") or ""
        )

        if not sid:
            raise RuntimeError(
                "assignment missing sample_id"
            )

        if sid in assignment_by_id:
            raise RuntimeError(
                f"duplicate assignment: {sid}"
            )

        assignment_by_id[sid] = row

    rgb_mapping = json.loads(
        RGB_MAPPING.read_text(
            encoding="utf-8"
        )
    )

    enriched: list[
        dict[str, Any]
    ] = []

    reserved_ids: set[str] = set()
    reserved_groups: set[str] = set()

    for source_row in reserved:
        row = dict(source_row)
        row.pop("_input_line_no", None)

        sid = str(
            row.get("sample_id") or ""
        )

        metadata = (
            row.get("metadata")
            or {}
        )

        group = str(
            metadata.get("group_key")
            or ""
        )

        if not sid or not group:
            raise RuntimeError(
                "reserved row missing "
                "sample_id/group_key"
            )

        if sid in reserved_ids:
            raise RuntimeError(
                f"duplicate reserved ID: {sid}"
            )

        if group in reserved_groups:
            raise RuntimeError(
                f"duplicate reserved group: "
                f"{group}"
            )

        reserved_ids.add(sid)
        reserved_groups.add(group)

        assignment = assignment_by_id.get(
            sid
        )

        if assignment is None:
            raise RuntimeError(
                f"assignment missing for {sid}"
            )

        if (
            assignment.get("split")
            != "RESERVED_TEST_CANDIDATE"
        ):
            raise RuntimeError(
                f"wrong split for {sid}"
            )

        if (
            str(
                assignment.get(
                    "group_key"
                )
                or ""
            )
            != group
        ):
            raise RuntimeError(
                f"group mismatch for {sid}"
            )

        source = str(
            assignment.get("source")
            or ""
        )

        family = str(
            assignment.get(
                "scenario_family"
            )
            or ""
        )

        assignment_role = str(
            assignment.get(
                "training_role"
            )
            or ""
        )

        if not source:
            raise RuntimeError(
                f"source missing for {sid}"
            )

        if not family:
            raise RuntimeError(
                f"family missing for {sid}"
            )

        if assignment_role not in {
            "POSITIVE",
            "HARD_NEGATIVE",
        }:
            raise RuntimeError(
                f"invalid assignment role "
                f"for {sid}: {assignment_role}"
            )

        inline_role = (
            row.get("quality")
            or {}
        ).get("training_role")

        if (
            inline_role is not None
            and inline_role != assignment_role
        ):
            raise RuntimeError(
                f"inline/assignment role "
                f"conflict for {sid}"
            )

        # Match the published D2 v1.1 validator contract:
        # legacy D1 rows have no inline training_role and are
        # reported as LEGACY_D1 rather than silently relabeled.
        release_role = (
            str(inline_role)
            if inline_role is not None
            else "LEGACY_D1"
        )

        rgb = rgb_mapping.get(sid)

        if not isinstance(rgb, dict):
            raise RuntimeError(
                f"RGB mapping missing "
                f"for {sid}"
            )

        rgb_ref = str(
            rgb.get("release_rgb_ref")
            or ""
        )

        if not rgb_ref:
            raise RuntimeError(
                f"RGB ref missing for {sid}"
            )

        rgb_path = ROOT / rgb_ref

        if not rgb_path.is_file():
            fallback = (
                SOURCE_RELEASE
                / "images"
                / Path(rgb_ref).name
            )

            if fallback.is_file():
                rgb_path = fallback
            else:
                raise RuntimeError(
                    f"RGB file missing "
                    f"for {sid}"
                )

        actual_sha = raw_sha256(
            rgb_path
        )

        actual_size = (
            rgb_path.stat().st_size
        )

        # D2 v1.1 content binding lives in visual_input.
        # rgb_mapping.json only maps original/release paths.
        visual = row.get("visual_input") or {}

        expected_sha = str(
            visual.get("rgb_sha256")
            or ""
        )

        expected_size = visual.get(
            "size_bytes"
        )

        if not expected_sha:
            raise RuntimeError(
                f"visual RGB SHA missing "
                f"for {sid}"
            )

        if expected_size is None:
            raise RuntimeError(
                f"visual RGB size missing "
                f"for {sid}"
            )

        if actual_sha != expected_sha:
            raise RuntimeError(
                f"RGB SHA mismatch "
                f"for {sid}"
            )

        if actual_size != expected_size:
            raise RuntimeError(
                f"RGB size mismatch "
                f"for {sid}"
            )

        enriched.append(
            {
                "sample_id": sid,
                "group_key": group,
                "source": source,
                "scenario_family": family,
                "scenario_id":
                    assignment.get(
                        "scenario_id"
                    ),
                "seed":
                    assignment.get(
                        "seed"
                    ),
                "release_training_role":
                    release_role,
                "assignment_training_role":
                    assignment_role,
                "inline_training_role":
                    inline_role,
                "selection_stratum": [
                    source,
                    family,
                    release_role,
                ],
                "selection_rank":
                    stable_rank(sid),
                "source_row": row,
                "rgb": {
                    "source_rgb_ref":
                        rgb_ref,
                    "sha256":
                        actual_sha,
                    "size_bytes":
                        actual_size,
                },
            }
        )

    if len(reserved_ids) != 540:
        raise RuntimeError(
            "reserved ID cardinality failed"
        )

    if len(reserved_groups) != 540:
        raise RuntimeError(
            "reserved group cardinality failed"
        )

    strata: dict[
        tuple[str, str, str],
        list[dict[str, Any]],
    ] = defaultdict(list)

    for item in enriched:
        key = tuple(
            item["selection_stratum"]
        )

        strata[key].append(item)

    stratum_counts = {
        key: len(items)
        for key, items in strata.items()
    }

    quotas = largest_remainder(
        stratum_counts,
        TARGET_COUNT,
    )

    selected: list[
        dict[str, Any]
    ] = []

    remainder: list[
        dict[str, Any]
    ] = []

    for key in sorted(strata):
        items = sorted(
            strata[key],
            key=lambda x: (
                x["selection_rank"],
                x["sample_id"],
            ),
        )

        quota = quotas[key]

        selected.extend(
            items[:quota]
        )

        remainder.extend(
            items[quota:]
        )

    selected.sort(
        key=lambda x: x["sample_id"]
    )

    remainder.sort(
        key=lambda x: x["sample_id"]
    )

    if len(selected) != 300:
        raise RuntimeError(
            f"selected != 300: "
            f"{len(selected)}"
        )

    if len(remainder) != 240:
        raise RuntimeError(
            f"remainder != 240: "
            f"{len(remainder)}"
        )

    selected_ids = {
        x["sample_id"]
        for x in selected
    }

    remainder_ids = {
        x["sample_id"]
        for x in remainder
    }

    if selected_ids & remainder_ids:
        raise RuntimeError(
            "selection/remainder "
            "sample overlap"
        )

    selected_groups = {
        x["group_key"]
        for x in selected
    }

    remainder_groups = {
        x["group_key"]
        for x in remainder
    }

    if (
        selected_groups
        & remainder_groups
    ):
        raise RuntimeError(
            "selection/remainder "
            "group overlap"
        )

    # --------------------------------------------------
    # Create release.
    # --------------------------------------------------

    OUT.mkdir(
        parents=True,
        exist_ok=False,
    )

    # Keep calibration rows semantically unchanged.
    calibration_rows = [
        x["source_row"]
        for x in selected
    ]

    write_jsonl(
        OUT / "calibration.jsonl",
        calibration_rows,
    )

    # Do not publish the remaining 240 as a
    # frozen benchmark. Only record identity/hash.
    remaining_ids = sorted(
        remainder_ids
    )

    (
        OUT
        / "unallocated_reserved_sample_ids.txt"
    ).write_text(
        "".join(
            f"{sid}\n"
            for sid in remaining_ids
        ),
        encoding="utf-8",
    )

    selection_rows = []

    for x in selected:
        selection_rows.append(
            {
                "sample_id":
                    x["sample_id"],
                "group_key":
                    x["group_key"],
                "source":
                    x["source"],
                "scenario_family":
                    x["scenario_family"],
                "scenario_id":
                    x["scenario_id"],
                "seed":
                    x["seed"],
                "release_training_role":
                    x[
                        "release_training_role"
                    ],
                "assignment_training_role":
                    x[
                        "assignment_training_role"
                    ],
                "inline_training_role":
                    x[
                        "inline_training_role"
                    ],
                "selection_stratum":
                    x["selection_stratum"],
                "selection_rank":
                    x["selection_rank"],
            }
        )

    write_jsonl(
        OUT / "selection_assignments.jsonl",
        selection_rows,
    )

    rgb_manifest = {
        x["sample_id"]: {
            "source_rgb_ref":
                x["rgb"][
                    "source_rgb_ref"
                ],
            "sha256":
                x["rgb"]["sha256"],
            "size_bytes":
                x["rgb"][
                    "size_bytes"
                ],
        }
        for x in selected
    }

    write_json(
        OUT / "rgb_manifest.json",
        rgb_manifest,
    )

    selected_source = Counter(
        x["source"]
        for x in selected
    )

    selected_family = Counter(
        x["scenario_family"]
        for x in selected
    )

    selected_role = Counter(
        x[
            "release_training_role"
        ]
        for x in selected
    )

    remaining_source = Counter(
        x["source"]
        for x in remainder
    )

    remaining_family = Counter(
        x["scenario_family"]
        for x in remainder
    )

    remaining_role = Counter(
        x[
            "release_training_role"
        ]
        for x in remainder
    )

    stratum_report = []

    for key in sorted(
        stratum_counts
    ):
        stratum_report.append(
            {
                "source": key[0],
                "scenario_family":
                    key[1],
                "training_role":
                    key[2],
                "pool_count":
                    stratum_counts[key],
                "selected_count":
                    quotas[key],
                "remaining_count":
                    (
                        stratum_counts[key]
                        - quotas[key]
                    ),
            }
        )

    coverage = {
        "schema_version": "1.0",
        "dataset_version":
            DATASET_VERSION,
        "pool_samples": 540,
        "pool_groups": 540,
        "selected_samples": 300,
        "selected_groups": 300,
        "unallocated_samples": 240,
        "unallocated_groups": 240,
        "selected_source_counts":
            dict(
                sorted(
                    selected_source.items()
                )
            ),
        "selected_family_counts":
            dict(
                sorted(
                    selected_family.items()
                )
            ),
        "selected_role_counts":
            dict(
                sorted(
                    selected_role.items()
                )
            ),
        "remaining_source_counts":
            dict(
                sorted(
                    remaining_source.items()
                )
            ),
        "remaining_family_counts":
            dict(
                sorted(
                    remaining_family.items()
                )
            ),
        "remaining_role_counts":
            dict(
                sorted(
                    remaining_role.items()
                )
            ),
        "joint_strata":
            stratum_report,
    }

    write_json(
        OUT
        / "calibration_coverage_report.json",
        coverage,
    )

    source_manifest_sha = (
        canonical_text_sha256(
            SOURCE_RELEASE_MANIFEST
        )
    )

    manifest = {
        "schema_version": "1.0",
        "dataset_version":
            DATASET_VERSION,
        "release_type":
            "calibration",
        "status":
            "FROZEN_CALIBRATION",
        "purpose":
            "PTQ calibration only",
        "target_count":
            300,
        "source_release":
            "d2_v1_1",
        "source_reserved_pool":
            (
                "challenge/dataset/"
                "releases/d2_v1_1/"
                "reserved_test_candidates.jsonl"
            ),
        "source_assignment_file":
            (
                "challenge/dataset/"
                "releases/d2_v1_1/"
                "source_split_assignments.jsonl"
            ),
        "source_rgb_mapping":
            (
                "challenge/dataset/"
                "releases/d2_v1_1/"
                "rgb_mapping.json"
            ),
        "source_release_manifest_sha256":
            source_manifest_sha,
        "selection": {
            "strategy":
                (
                    "joint stratification "
                    "by source x "
                    "scenario_family x "
                    "published D2 "
                    "training_role"
                ),
            "allocation":
                "largest_remainder",
            "ranking":
                "sha256",
            "selection_salt":
                SELECTION_SALT,
            "group_atomic":
                True,
        },
        "governance": {
            "source_release_mutated":
                False,
            "calibration_is_training":
                False,
            "calibration_is_dev":
                False,
            "calibration_is_frozen_test":
                False,
            "remaining_240_are_frozen_test":
                False,
            "remaining_240_policy":
                (
                    "UNALLOCATED_RESERVED_POOL; "
                    "B2 must independently "
                    "decide future benchmark "
                    "membership."
                ),
            "future_b2_policy":
                (
                    "B2 Frozen Benchmark "
                    "must exclude all "
                    "Calibration v1 "
                    "sample_ids and group_keys."
                ),
        },
        "counts": {
            "source_pool": 540,
            "calibration": 300,
            "unallocated_reserved": 240,
        },
    }

    write_json(
        OUT / "calibration_manifest.json",
        manifest,
    )

    readme = """# B1 Calibration v1

This directory is a frozen PTQ calibration asset.

## Counts

- Source reserved pool: 540 samples / 540 groups
- Calibration: 300 samples / 300 groups
- Remaining unallocated reserved pool: 240 samples / 240 groups

## Selection

Selection is deterministic and group-atomic.

The source D2 v1.1 reserved pool is joined with
`source_split_assignments.jsonl` by `sample_id`.

Authoritative selection dimensions are:

- source
- scenario_family
- training_role

Quota allocation uses proportional largest-remainder rounding.
Rows inside each joint stratum are ranked by SHA256 with the
frozen selection salt recorded in `calibration_manifest.json`.

## Governance

Calibration v1:

- is NOT training data
- is NOT development/validation data
- is NOT Frozen Test
- must not be changed based on PTQ performance
- remains bound to the immutable D2 v1.1 source release

The remaining 240 reserved samples are NOT automatically
promoted to Frozen Test. B2 owns independent benchmark freeze.

Future B2 benchmark construction must exclude every
Calibration v1 sample_id and group_key.

Historical D2 v1.1 files are not modified.
"""

    (
        OUT / "README.md"
    ).write_text(
        readme,
        encoding="utf-8",
    )

    # --------------------------------------------------
    # Content hashes.
    # --------------------------------------------------

    hash_targets = sorted(
        p
        for p in OUT.iterdir()
        if p.is_file()
        and p.name != "hashes.sha256"
    )

    with (
        OUT / "hashes.sha256"
    ).open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as f:
        for path in hash_targets:
            f.write(
                f"{raw_sha256(path)}  "
                f"{path.name}\n"
            )

    # --------------------------------------------------
    # Final report.
    # --------------------------------------------------

    print(
        "CALIBRATION_BUILD=PASS"
    )

    print(
        "POOL_SAMPLES=540"
    )

    print(
        "CALIBRATION_SAMPLES="
        f"{len(selected)}"
    )

    print(
        "CALIBRATION_GROUPS="
        f"{len(selected_groups)}"
    )

    print(
        "UNALLOCATED_RESERVED="
        f"{len(remainder)}"
    )

    print(
        "SELECTED_SOURCE_COUNTS="
        f"{dict(sorted(selected_source.items()))}"
    )

    print(
        "SELECTED_FAMILY_COUNTS="
        f"{dict(sorted(selected_family.items()))}"
    )

    print(
        "SELECTED_ROLE_COUNTS="
        f"{dict(sorted(selected_role.items()))}"
    )

    print(
        "MANIFEST_SHA256="
        f"{canonical_text_sha256(OUT / 'calibration_manifest.json')}"
    )

    print(
        "CALIBRATION_SHA256="
        f"{canonical_text_sha256(OUT / 'calibration.jsonl')}"
    )


if __name__ == "__main__":
    main()
