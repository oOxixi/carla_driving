#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

DATASET = ROOT / "challenge/dataset"

OUT = (
    DATASET
    / "attestations"
    / "b1_legacy_template_identity_recovery_v1"
)

CLOSEOUT = (
    DATASET
    / "governance"
    / "b1_closeout_v1"
)

IV = (
    CLOSEOUT
    / "independent_validation_v1"
)

B2_CASE_MANIFEST = (
    ROOT
    / "challenge"
    / "benchmark"
    / "case_manifest.py"
)

HIL_FROZEN_ROOT = (
    ROOT
    / "challenge"
    / "hil"
    / "frozen"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []

    for line_no, line in enumerate(
        path.read_text(
            encoding="utf-8"
        ).splitlines(),
        start=1,
    ):
        if not line.strip():
            continue

        value = json.loads(line)

        if not isinstance(value, dict):
            raise RuntimeError(
                f"{path}:{line_no}: "
                "JSONL row is not an object"
            )

        rows.append(value)

    return rows


def write_json(
    path: Path,
    value: Any,
) -> None:
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def normalize_source_text(
    value: str,
) -> str:
    # Must match challenge/benchmark/case_manifest.py.
    normalized = unicodedata.normalize(
        "NFKC",
        value,
    )
    normalized = " ".join(
        normalized.split()
    )
    return normalized.casefold()


def governed_sources() -> dict[str, Path]:
    sources = {
        "d2_v1_1:train":
            DATASET
            / "releases"
            / "d2_v1_1"
            / "train.jsonl",

        "d2_v1_1:dev":
            DATASET
            / "releases"
            / "d2_v1_1"
            / "val.jsonl",

        "b1_independent_validation_v1":
            IV
            / "cases.jsonl",
    }

    for release_id in (
        "d3_wave1_addon_v1",
        "d3_wave2_safe_short_v1",
        "d3_targeted_gap_strict_v1",
        "d3_turn_gap_60_strict_v1",
        "d3_gap300_strict_v1",
        "b1_ms34_supplement_v1",
    ):
        root = (
            DATASET
            / "releases"
            / release_id
        )

        sources[
            f"{release_id}:train"
        ] = (
            root
            / "train_addition.jsonl"
        )

        sources[
            f"{release_id}:dev"
        ] = (
            root
            / "val_addition.jsonl"
        )

    return sources


def load_governed_rows():
    all_rows = []
    by_sample_id = {}

    role_counts = Counter()

    for source_name, path in (
        governed_sources().items()
    ):
        rows = load_jsonl(path)

        if source_name.endswith(":train"):
            role = "TRAIN"
        elif source_name.endswith(":dev"):
            role = "DEV"
        else:
            role = "INDEPENDENT_VALIDATION"

        for row in rows:
            sid = row.get("sample_id")

            if (
                not isinstance(sid, str)
                or not sid
            ):
                raise RuntimeError(
                    f"{source_name}: "
                    "missing sample_id"
                )

            if sid in by_sample_id:
                raise RuntimeError(
                    "duplicate governed sample_id: "
                    + sid
                )

            entry = {
                "dataset_role": role,
                "canonical_source":
                    source_name,
                "row": row,
            }

            by_sample_id[sid] = entry
            all_rows.append(entry)
            role_counts[role] += 1

    return (
        all_rows,
        by_sample_id,
        role_counts,
    )


CANDIDATE_LINEAGE_KEYS = (
    "template_id",
    "template_ref",
    "template_name",
    "instruction_id",
    "instruction_ref",
    "language_id",
    "language_record",
    "benchmark_id",
    "benchmark_record",
    "record_id",
    "source_record_id",
    "variant_id",
    "utterance_id",
)


def scan_object_for_lineage(
    value: Any,
    hits: Counter,
    prefix: str = "",
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            path = (
                f"{prefix}.{key}"
                if prefix
                else key
            )

            key_lower = key.lower()

            if any(
                token == key_lower
                or token in key_lower
                for token
                in CANDIDATE_LINEAGE_KEYS
            ):
                hits[path] += 1

            scan_object_for_lineage(
                child,
                hits,
                path,
            )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_object_for_lineage(
                child,
                hits,
                f"{prefix}[{index}]",
            )


def audit_source_logs(
    all_rows,
):
    source_logs: dict[
        str,
        list[str],
    ] = defaultdict(list)

    for item in all_rows:
        row = item["row"]
        sid = row["sample_id"]

        md = row.get("metadata") or {}
        log_path = md.get("source_log")

        if (
            isinstance(log_path, str)
            and log_path
        ):
            source_logs[
                log_path
            ].append(sid)

    stats = Counter()
    lineage_hits = Counter()

    for log_path in sorted(
        source_logs
    ):
        path = Path(log_path)

        if not path.is_file():
            stats["log_missing"] += 1
            continue

        stats["log_found"] += 1

        this_log_hits = Counter()

        for line in path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines():
            if not line.strip():
                continue

            try:
                obj = json.loads(line)
            except Exception:
                continue

            scan_object_for_lineage(
                obj,
                this_log_hits,
            )

        if this_log_hits:
            stats[
                "logs_with_candidate_lineage"
            ] += 1

            lineage_hits.update(
                this_log_hits
            )
        else:
            stats[
                "logs_without_candidate_lineage"
            ] += 1

    return (
        source_logs,
        stats,
        lineage_hits,
    )


def audit_scenario_linkage(
    all_rows,
):
    stats = Counter()

    for item in all_rows:
        row = item["row"]

        md = row.get("metadata") or {}

        scenario_path = (
            md.get("scenario_config_path")
        )
        command_id = (
            md.get("command_id")
        )

        if not (
            isinstance(scenario_path, str)
            and scenario_path
        ):
            stats[
                "missing_scenario_config_path"
            ] += 1
            continue

        path = ROOT / scenario_path

        if not path.is_file():
            stats[
                "scenario_file_missing"
            ] += 1
            continue

        stats[
            "scenario_file_found"
        ] += 1

        data = load_json(path)

        commands = (
            data.get("commands")
            if isinstance(data, dict)
            else None
        )

        if not isinstance(
            commands,
            list,
        ):
            stats[
                "scenario_commands_missing"
            ] += 1
            continue

        matches = [
            command
            for command in commands
            if isinstance(command, dict)
            and command.get(
                "command_id"
            ) == command_id
        ]

        if not matches:
            stats[
                "command_id_not_found"
            ] += 1
        elif len(matches) == 1:
            stats[
                "command_id_unique_match"
            ] += 1
        else:
            stats[
                "command_id_ambiguous"
            ] += 1

    return stats


def historical_observed_sets():
    return (
        "d2_v1_1_val",
        "d3_wave2_safe_short_v1_val",
        "d3_targeted_gap_strict_v1_val",
        "d3_turn_gap_60_strict_v1_val",
    )


def load_historical_observed_ids():
    observed_ids = set()
    set_bindings = {}

    for name in historical_observed_sets():
        root = (
            HIL_FROZEN_ROOT / name
        )

        manifest_path = (
            root / "manifest.json"
        )
        cases_path = (
            root / "cases.jsonl"
        )

        if not manifest_path.is_file():
            raise RuntimeError(
                "missing HIL manifest: "
                + str(manifest_path)
            )

        if not cases_path.is_file():
            raise RuntimeError(
                "missing HIL cases: "
                + str(cases_path)
            )

        manifest = load_json(
            manifest_path
        )

        rows = load_jsonl(
            cases_path
        )

        local_ids = set()

        for row in rows:
            sid = row.get("sample_id")

            if not (
                isinstance(sid, str)
                and sid
            ):
                raise RuntimeError(
                    f"{cases_path}: "
                    "missing sample_id"
                )

            local_ids.add(sid)
            observed_ids.add(sid)

        set_bindings[name] = {
            "case_count":
                len(rows),

            "unique_sample_ids":
                len(local_ids),

            "case_set_digest_sha256":
                manifest.get(
                    "case_set_digest_sha256"
                ),

            "manifest_path":
                str(
                    manifest_path.relative_to(
                        ROOT
                    )
                ),

            "manifest_sha256":
                sha256_file(
                    manifest_path
                ),

            "cases_path":
                str(
                    cases_path.relative_to(
                        ROOT
                    )
                ),

            "cases_sha256":
                sha256_file(
                    cases_path
                ),
        }

    return (
        observed_ids,
        set_bindings,
    )


def build_observed_exclusion(
    observed_ids,
    by_sample_id,
):
    rows = []

    groups = set()
    scenarios = set()
    source_text_hashes = set()

    missing = []

    for sid in sorted(
        observed_ids
    ):
        item = by_sample_id.get(
            sid
        )

        if item is None:
            missing.append(sid)
            continue

        row = item["row"]

        md = row.get(
            "metadata"
        ) or {}

        request = row.get(
            "model_request"
        ) or {}

        group_key = md.get(
            "group_key"
        )

        scenario_id = md.get(
            "scenario_id"
        )

        source_text = request.get(
            "source_text"
        )

        source_text_sha256 = None

        if (
            isinstance(
                source_text,
                str,
            )
            and source_text.strip()
        ):
            source_text_sha256 = (
                sha256_text(
                    normalize_source_text(
                        source_text
                    )
                )
            )

            source_text_hashes.add(
                source_text_sha256
            )

        if (
            isinstance(
                group_key,
                str,
            )
            and group_key
        ):
            groups.add(
                group_key
            )

        if (
            isinstance(
                scenario_id,
                str,
            )
            and scenario_id
        ):
            scenarios.add(
                scenario_id
            )

        rows.append({
            "sample_id":
                sid,

            "canonical_source":
                item[
                    "canonical_source"
                ],

            "dataset_role":
                item[
                    "dataset_role"
                ],

            "group_key":
                group_key,

            "scenario_id":
                scenario_id,

            "normalized_source_text_sha256":
                source_text_sha256,
        })

    return (
        rows,
        groups,
        scenarios,
        source_text_hashes,
        missing,
    )


def main() -> int:
    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        all_rows,
        by_sample_id,
        role_counts,
    ) = load_governed_rows()

    if len(all_rows) != 7435:
        raise RuntimeError(
            "governed row count "
            f"{len(all_rows)} != 7435"
        )

    expected_roles = {
        "TRAIN": 6037,
        "DEV": 1158,
        "INDEPENDENT_VALIDATION":
            240,
    }

    if dict(role_counts) != (
        expected_roles
    ):
        raise RuntimeError(
            "role counts mismatch: "
            + repr(
                dict(role_counts)
            )
        )

    explicit_template_count = 0

    for item in all_rows:
        md = (
            item["row"].get(
                "metadata"
            )
            or {}
        )

        template_id = md.get(
            "template_id"
        )

        if (
            isinstance(
                template_id,
                str,
            )
            and template_id.strip()
        ):
            explicit_template_count += 1

    (
        source_logs,
        source_log_stats,
        source_log_hits,
    ) = audit_source_logs(
        all_rows
    )

    scenario_stats = (
        audit_scenario_linkage(
            all_rows
        )
    )

    (
        observed_ids,
        observed_set_bindings,
    ) = (
        load_historical_observed_ids()
    )

    (
        observed_rows,
        groups,
        scenarios,
        source_text_hashes,
        missing_observed,
    ) = build_observed_exclusion(
        observed_ids,
        by_sample_id,
    )

    if missing_observed:
        raise RuntimeError(
            "observed samples missing from "
            "canonical B1 data: "
            + repr(
                missing_observed[:20]
            )
        )

    if len(observed_ids) != 723:
        raise RuntimeError(
            "observed sample union "
            f"{len(observed_ids)} != 723"
        )

    if len(groups) != 645:
        raise RuntimeError(
            "observed groups "
            f"{len(groups)} != 645"
        )

    if len(scenarios) != 95:
        raise RuntimeError(
            "observed scenarios "
            f"{len(scenarios)} != 95"
        )

    if (
        source_log_stats.get(
            "log_found",
            0,
        )
        != 5293
    ):
        raise RuntimeError(
            "source-log found count "
            "does not equal 5293"
        )

    if (
        source_log_stats.get(
            "logs_with_candidate_lineage",
            0,
        )
        != 0
    ):
        raise RuntimeError(
            "candidate template lineage "
            "was discovered; "
            "manual review required"
        )

    if source_log_hits:
        raise RuntimeError(
            "unexpected candidate "
            "lineage fields found"
        )

    observed_jsonl = (
        OUT
        / "observed_identity_rows.jsonl"
    )

    observed_jsonl.write_text(
        "".join(
            json.dumps(
                row,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
            for row in observed_rows
        ),
        encoding="utf-8",
    )

    (
        OUT
        / "observed_sample_ids.txt"
    ).write_text(
        "\n".join(
            sorted(observed_ids)
        )
        + "\n",
        encoding="utf-8",
    )

    (
        OUT
        / "observed_group_keys.txt"
    ).write_text(
        "\n".join(
            sorted(groups)
        )
        + "\n",
        encoding="utf-8",
    )

    (
        OUT
        / "observed_scenario_ids.txt"
    ).write_text(
        "\n".join(
            sorted(scenarios)
        )
        + "\n",
        encoding="utf-8",
    )

    (
        OUT
        / "observed_source_text_sha256.txt"
    ).write_text(
        "\n".join(
            sorted(
                source_text_hashes
            )
        )
        + "\n",
        encoding="utf-8",
    )

    recovery_attestation = {
        "schema_version":
            "b1-legacy-template-identity-recovery-v1",

        "status":
            "HISTORICAL_TEMPLATE_LINEAGE_UNRECOVERABLE",

        "scope": {
            "governed_train_samples":
                6037,

            "governed_dev_samples":
                1158,

            "independent_validation_samples":
                240,

            "total_samples":
                7435,
        },

        "findings": {
            "explicit_metadata_template_id":
                explicit_template_count,

            "unique_source_logs":
                len(source_logs),

            "source_log_audit":
                dict(
                    sorted(
                        source_log_stats.items()
                    )
                ),

            "source_log_candidate_lineage_fields":
                dict(
                    sorted(
                        source_log_hits.items()
                    )
                ),

            "scenario_linkage_audit":
                dict(
                    sorted(
                        scenario_stats.items()
                    )
                ),
        },

        "conclusion": {
            "formal_sample_to_template_sidecar_issuable":
                False,

            "reason":
                "No explicit historical template identity "
                "or deterministic template-registry lineage "
                "is present in the governed sample metadata, "
                "scenario-command records, or 5293 unique "
                "historical source logs.",

            "inference_from_source_text_permitted":
                False,

            "inference_from_scenario_id_permitted":
                False,

            "synthetic_per_sample_template_ids_permitted":
                False,

            "independent_validation_cases_mutated":
                False,

            "historical_releases_mutated":
                False,
        },

        "b2_contract": {
            "path":
                str(
                    B2_CASE_MANIFEST.relative_to(
                        ROOT
                    )
                ),

            "sha256":
                sha256_file(
                    B2_CASE_MANIFEST
                ),

            "behavior":
                "FAIL_CLOSED_IF_TEMPLATE_IDENTITY_MISSING",
        },
    }

    write_json(
        OUT
        / "recovery_attestation.json",
        recovery_attestation,
    )

    exclusion_manifest = {
        "schema_version":
            "b1-observed-exclusion-v1",

        "status":
            "PASS",

        "purpose":
            "Pre-acquisition exclusion inventory for "
            "future B1 targeted collection.",

        "method":
            "Historical HIL observed sample IDs are "
            "deterministically joined to governed B1 "
            "canonical rows by sample_id.",

        "counts": {
            "sample_ids":
                len(observed_ids),

            "group_keys":
                len(groups),

            "scenario_ids":
                len(scenarios),

            "normalized_source_text_sha256":
                len(
                    source_text_hashes
                ),

            "missing_canonical_rows":
                len(
                    missing_observed
                ),
        },

        "sets":
            observed_set_bindings,

        "governance": {
            "sample_id_is_identity":
                True,

            "group_key_is_identity":
                True,

            "scenario_id_is_exclusion_identity":
                True,

            "source_text_sha256_is_literal_duplicate_detection_only":
                True,

            "source_text_sha256_is_template_identity":
                False,

            "legacy_template_overlap_computable":
                False,

            "legacy_template_overlap_reason":
                "Historical B1/B2/B3 assets do not "
                "carry authoritative template identity.",
        },

        "files": {
            "observed_identity_rows":
                "observed_identity_rows.jsonl",

            "observed_sample_ids":
                "observed_sample_ids.txt",

            "observed_group_keys":
                "observed_group_keys.txt",

            "observed_scenario_ids":
                "observed_scenario_ids.txt",

            "observed_source_text_sha256":
                "observed_source_text_sha256.txt",
        },
    }

    write_json(
        OUT
        / "observed_exclusion_manifest.json",
        exclusion_manifest,
    )

    provenance_manifest = {
        "schema_version":
            "b1-template-gap-recovery-provenance-v1",

        "status":
            "PASS",

        "bindings": {
            "b1_closeout_report": {
                "path":
                    str(
                        (
                            CLOSEOUT
                            / "B1_CLOSEOUT_REPORT.json"
                        ).relative_to(
                            ROOT
                        )
                    ),

                "sha256":
                    sha256_file(
                        CLOSEOUT
                        / "B1_CLOSEOUT_REPORT.json"
                    ),
            },

            "governed_release_manifest": {
                "path":
                    str(
                        (
                            CLOSEOUT
                            / "governed_release_manifest.json"
                        ).relative_to(
                            ROOT
                        )
                    ),

                "sha256":
                    sha256_file(
                        CLOSEOUT
                        / "governed_release_manifest.json"
                    ),
            },

            "independent_validation_dataset_identity":
                {
                    "path":
                        str(
                            (
                                IV
                                / "dataset_identity.json"
                            ).relative_to(
                                ROOT
                            )
                        ),

                    "sha256":
                        sha256_file(
                            IV
                            / "dataset_identity.json"
                        ),
                },

            "independent_validation_cases":
                {
                    "path":
                        str(
                            (
                                IV
                                / "cases.jsonl"
                            ).relative_to(
                                ROOT
                            )
                        ),

                    "sha256":
                        sha256_file(
                            IV
                            / "cases.jsonl"
                        ),
                },

            "b2_case_manifest_contract":
                {
                    "path":
                        str(
                            B2_CASE_MANIFEST.relative_to(
                                ROOT
                            )
                        ),

                    "sha256":
                        sha256_file(
                            B2_CASE_MANIFEST
                        ),
                },
        },

        "historical_observed_sets":
            observed_set_bindings,

        "immutability": {
            "b1_closeout_v1_modified":
                False,

            "independent_validation_cases_modified":
                False,

            "historical_releases_modified":
                False,
        },
    }

    write_json(
        OUT
        / "provenance_manifest.json",
        provenance_manifest,
    )

    generated = [
        OUT / "recovery_attestation.json",
        OUT / "observed_exclusion_manifest.json",
        OUT / "observed_identity_rows.jsonl",
        OUT / "observed_sample_ids.txt",
        OUT / "observed_group_keys.txt",
        OUT / "observed_scenario_ids.txt",
        OUT / "observed_source_text_sha256.txt",
        OUT / "provenance_manifest.json",
    ]

    sums = []

    for path in sorted(
        generated,
        key=lambda p:
            p.relative_to(
                OUT
            ).as_posix(),
    ):
        sums.append(
            sha256_file(path)
            + "  "
            + path.relative_to(
                OUT
            ).as_posix()
        )

    (
        OUT
        / "SHA256SUMS"
    ).write_text(
        "\n".join(
            sums
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "===== B1 LEGACY TEMPLATE IDENTITY "
        "RECOVERY V1 ====="
    )
    print(
        "governed samples             =",
        len(all_rows),
    )
    print(
        "explicit template_id         =",
        explicit_template_count,
    )
    print(
        "unique source logs           =",
        len(source_logs),
    )
    print(
        "source logs with lineage     =",
        source_log_stats.get(
            "logs_with_candidate_lineage",
            0,
        ),
    )
    print(
        "observed samples             =",
        len(observed_ids),
    )
    print(
        "observed groups              =",
        len(groups),
    )
    print(
        "observed scenarios           =",
        len(scenarios),
    )
    print(
        "observed text hashes         =",
        len(
            source_text_hashes
        ),
    )
    print(
        "legacy template identity     =",
        recovery_attestation[
            "status"
        ],
    )
    print(
        "observed exclusion inventory = PASS"
    )
    print("BUILD                        = PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
