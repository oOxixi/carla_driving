# B1 Data Closeout Handoff

## Status

`B1_DATA_CLOSEOUT = PASS`

B1 data collection is paused. Historical releases remain immutable.

## Governed identities

- Governed Train: **6037**
- Governed Dev: **1158**
- Calibration v1: **300 samples / 300 groups**
- Independent Validation v1: **240 samples / 240 groups**
- Frozen Test: **NOT_ASSIGNED_BY_B1**

## Independent Validation

Dataset version: `b1_independent_validation_v1`

The set is exactly:

`D2 v1.1 reserved_test_candidates (540) - Calibration v1 (300)`

No additional ranking, relabeling, or sampling was applied.

It must not be used for A3 training, development tuning,
hyperparameter selection, or error-driven iteration.

## Gap300

The immutable Gap300 release is not modified.

Its historical provenance is supplemented through the existing
Gap300 provenance addendum and Teacher provenance attestation.
`attestations/gap300_provenance_binding.json` binds those artifacts
to the release hashes.

## MS34 3-step / 4-step supplement

`b1_ms34_supplement_v1` is included in the governed dataset:

- Train positive: 30
- Dev positive: 4
- Hard negative: 1
- 3-step positives: 17
- 4-step positives: 17

Its release remains immutable. A separate Teacher provenance
addendum clarifies that recorded `metadata.teacher_git_sha` is the
acquisition/runtime checkout identity and is not silently rewritten
as the canonical pinned Teacher identity.

## Teacher policy

Historical releases preserve their recorded provenance.

Future formal Teacher work must use the current pinned Teacher policy
bound by `challenge/teacher_pinned_manifest_v4.json`.

## Primary files

- `governed_release_manifest.json`
- `teacher_provenance_registry.json`
- `calibration_identity.json`
- `leakage_audit.json`
- `independent_validation_v1/case_manifest.json`
- `independent_validation_v1/case_set_digest.json`
- `independent_validation_v1/dataset_identity.json`
- `B1_CLOSEOUT_REPORT.json`
- `SHA256SUMS`

This handoff makes no B2 accuracy or gate claim.
