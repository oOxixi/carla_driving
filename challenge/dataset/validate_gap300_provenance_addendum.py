import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REL = (
    ROOT
    / "challenge/dataset/releases/d3_gap300_strict_v1"
)

ADD = (
    ROOT
    / "challenge/dataset/attestations/"
    "d3_gap300_strict_v1_provenance_addendum_v1"
)

PINNED = ROOT / "challenge/teacher_pinned_manifest_v4.json"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path):
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main():
    errors = []

    required = [
        ADD / "gap300_provenance_addendum.json",
        ADD / "GAP300_PROVENANCE_ADDENDUM.md",
        ADD / "SHA256SUMS",
        REL / "release_manifest.json",
        REL / "provenance_manifest.json",
        REL / "b1_release_lock.sha256",
        REL / "B1_CONTENT_BOUND_PASS.json",
        PINNED,
    ]

    for p in required:
        if not p.is_file():
            errors.append(f"missing file: {p}")

    if errors:
        for e in errors:
            print("ERROR:", e)
        print("GAP300_PROVENANCE_ADDENDUM_GATE=FAIL")
        return 2

    a = load_json(
        ADD / "gap300_provenance_addendum.json"
    )

    release = load_json(
        REL / "release_manifest.json"
    )

    prov = load_json(
        REL / "provenance_manifest.json"
    )

    pinned = load_json(PINNED)

    rows = (
        load_jsonl(REL / "train_addition.jsonl")
        + load_jsonl(REL / "val_addition.jsonl")
    )

    if len(rows) != 820:
        errors.append(f"Gap300 row count={len(rows)} != 820")

    sample_ids = [r["sample_id"] for r in rows]
    if len(set(sample_ids)) != 820:
        errors.append("Gap300 sample IDs are not unique")

    model_counts = Counter(
        (r.get("metadata") or {}).get("teacher_model_id")
        for r in rows
    )

    mode_counts = Counter(
        (r.get("metadata") or {}).get("teacher_mode")
        for r in rows
    )

    git_counts = Counter(
        (r.get("metadata") or {}).get("teacher_git_sha")
        for r in rows
    )

    service_counts = Counter(
        (r.get("metadata") or {}).get("teacher_service_url")
        for r in rows
    )

    family_counts = Counter(
        (r.get("metadata") or {}).get("scenario_family")
        for r in rows
    )

    cross = Counter(
        (
            (r.get("metadata") or {}).get("teacher_git_sha"),
            (r.get("metadata") or {}).get("teacher_service_url"),
            (r.get("metadata") or {}).get("scenario_family"),
        )
        for r in rows
    )

    if model_counts != Counter(
        {"Qwen/Qwen3.5-2B": 820}
    ):
        errors.append(
            f"teacher model distribution mismatch: {dict(model_counts)}"
        )

    if mode_counts != Counter({"planner_v2": 820}):
        errors.append(
            f"teacher mode distribution mismatch: {dict(mode_counts)}"
        )

    expected_git = Counter({
        "95668ba3a466ae0dfcd73982f5a4a0d210b524c1": 770,
        "e150ae598d95cb024faebc1699b872d0de899e91": 50,
    })

    if git_counts != expected_git:
        errors.append(
            f"teacher_git_sha distribution mismatch: {dict(git_counts)}"
        )

    if service_counts != Counter({
        "http://127.0.0.1:18004": 770,
        "http://127.0.0.1:18009": 50,
    }):
        errors.append(
            f"service distribution mismatch: {dict(service_counts)}"
        )

    if family_counts != Counter({
        "qwen_fullchain": 770,
        "regression": 50,
    }):
        errors.append(
            f"family distribution mismatch: {dict(family_counts)}"
        )

    expected_cross = Counter({
        (
            "95668ba3a466ae0dfcd73982f5a4a0d210b524c1",
            "http://127.0.0.1:18004",
            "qwen_fullchain",
        ): 770,
        (
            "e150ae598d95cb024faebc1699b872d0de899e91",
            "http://127.0.0.1:18009",
            "regression",
        ): 50,
    })

    if cross != expected_cross:
        errors.append(
            f"runtime/service/family mapping mismatch: {dict(cross)}"
        )

    binding = a["historical_release_binding"]

    file_bindings = {
        "release_manifest_sha256":
            REL / "release_manifest.json",
        "provenance_manifest_sha256":
            REL / "provenance_manifest.json",
        "release_lock_sha256":
            REL / "b1_release_lock.sha256",
        "content_bound_pass_sha256":
            REL / "B1_CONTENT_BOUND_PASS.json",
    }

    for key, path in file_bindings.items():
        actual = sha256(path)
        if binding.get(key) != actual:
            errors.append(
                f"{key} mismatch: "
                f"{binding.get(key)} != {actual}"
            )

    if binding.get("image_set_canonical_sha256") != (
        release["image_set"]["canonical_sha256"]
    ):
        errors.append("release image-set binding mismatch")

    if binding.get("source_dataset_sha256") != (
        prov["source_dataset_sha256"]
    ):
        errors.append("source dataset binding mismatch")

    if binding.get("source_release_manifest_sha256") != (
        prov["source_release_manifest_sha256"]
    ):
        errors.append("source release manifest binding mismatch")

    if binding.get("source_image_set_sha256") != (
        prov["source_image_set_sha256"]
    ):
        errors.append("source image-set binding mismatch")

    policy = a["current_pinned_teacher_policy"]

    if policy.get("manifest_sha256") != sha256(PINNED):
        errors.append("pinned Teacher manifest SHA mismatch")

    pinned_checks = {
        "teacher_profile":
            pinned["teacher_profile"],
        "teacher_git_sha":
            pinned["teacher_git_sha"],
        "model_id":
            pinned["model_id"],
        "model_revision":
            pinned["model_revision"],
        "artifact_fingerprint":
            pinned["model_artifact_sha256"],
        "quantization":
            pinned.get("quantization"),
        "dtype":
            pinned["dtype"],
    }

    for key, expected in pinned_checks.items():
        if policy.get(key) != expected:
            errors.append(
                f"pinned Teacher field mismatch: {key}"
            )

    expected_missing = {
        "teacher_profile",
        "model_revision",
        "artifact_fingerprint",
        "dtype",
        "quantization",
    }

    if set(
        a["sample_level_missing_identity_fields"]
    ) != expected_missing:
        errors.append(
            "sample-level missing identity declaration mismatch"
        )

    if a.get("status") != (
        "PASS_WITH_HISTORICAL_IDENTITY_LIMITATION"
    ):
        errors.append("attestation status mismatch")

    if a.get("attestation_type") != (
        "HISTORICAL_PROVENANCE_ADDENDUM_CONTENT_BOUND_UNSIGNED"
    ):
        errors.append("attestation type mismatch")

    sums = {}
    for line in (
        ADD / "SHA256SUMS"
    ).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        sums[name.strip()] = digest

    expected_hashes = {
        "GAP300_PROVENANCE_ADDENDUM.md":
            sha256(ADD / "GAP300_PROVENANCE_ADDENDUM.md"),
        "gap300_provenance_addendum.json":
            sha256(ADD / "gap300_provenance_addendum.json"),
    }

    if sums != expected_hashes:
        errors.append(
            f"SHA256SUMS mismatch: {sums}"
        )

    print("GAP300_ROWS =", len(rows))
    print("MODEL_COUNTS =", dict(model_counts))
    print("MODE_COUNTS =", dict(mode_counts))
    print("GIT_COUNTS =", dict(git_counts))
    print("SERVICE_COUNTS =", dict(service_counts))
    print("FAMILY_COUNTS =", dict(family_counts))
    print("CROSS_COUNTS =", dict(cross))
    print(
        "PINNED_TEACHER_MANIFEST_SHA256 =",
        sha256(PINNED),
    )
    print(
        "ADDENDUM_JSON_SHA256 =",
        sha256(ADD / "gap300_provenance_addendum.json"),
    )
    print(
        "ADDENDUM_MD_SHA256 =",
        sha256(ADD / "GAP300_PROVENANCE_ADDENDUM.md"),
    )
    print("ERRORS =", len(errors))

    for e in errors:
        print("ERROR:", e)

    print(
        "GAP300_PROVENANCE_ADDENDUM_GATE="
        + ("PASS" if not errors else "FAIL")
    )

    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
