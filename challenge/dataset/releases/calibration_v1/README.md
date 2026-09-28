# B1 Calibration v1

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
