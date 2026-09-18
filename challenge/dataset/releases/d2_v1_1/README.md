# B1 D2 Dataset Release v1.1

B1-signed corrected downstream release for D2 Student development.

## Release status

B1_SIGNED_PASS

This release supersedes `d2_v1` for new downstream training runs.

## Splits

- Train: 2513
- Validation: 539
- Reserved test candidates: 540
- Total released samples: 3592
- RGB images: 3592
- Quarantined legacy D1 samples: 8

The split remains group-aware.

`reserved_test_candidates.jsonl` must not be used for training,
hyperparameter tuning, or checkpoint selection.

## D1 correction

Eight legacy D1 samples were quarantined because their terminal-state
metadata was internally inconsistent:

- run_status = FAILED
- command_terminal_status = SUCCEEDED
- plan_terminal_state = SUCCEEDED

The original rows are retained for provenance under:

    quarantine/d1_terminal_state_anomalies.jsonl

## Files

Training:

    train.jsonl

Development/model selection:

    val.jsonl

Reserved evaluation candidate set:

    reserved_test_candidates.jsonl

RGB assets:

    images/

The JSONL RGB references are portable repository-relative paths.

## Manifests

`release_manifest.json` is the authoritative B1 release manifest for
this portable v1.1 release.

`source_split_manifest.json`, `source_split_report.json`, and
`source_split_assignments.jsonl` are preserved historical artifacts
from the original D2 provisional split. Their original JSONL hashes
must not be used to verify this path-rewritten release.

## Teacher

Teacher profile:

    b1-pinned-teacher-v4

Teacher Git SHA:

    95e97b00def8ec36f12937da34ce8bb9082c4a04

Teacher tag:

    teacher-baseline-v4
