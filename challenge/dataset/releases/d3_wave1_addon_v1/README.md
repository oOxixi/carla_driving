# D3 Wave1 Additive Release v1

This release is an additive B1 dataset release on top of `d2_v1_1`.

It does not modify or supersede `d2_v1_1`.

## Counts

- Source runs: 2000
- Source samples: 2398
- Strict-positive: 2055
- Train addition: 1747
- Val addition: 308
- Hard-negative addition: 308
- Terminal-inconsistent positive quarantine: 35
- RGB files: 2363

## Governance

Normal positive supervision requires all of:

- `quality.valid_for_training == true`
- `quality.training_role == POSITIVE`
- `run_status == SUCCEEDED`
- `command_terminal_status == SUCCEEDED`
- `plan_terminal_state == SUCCEEDED`
- `scenario_acceptance_passed == true`

35 rows that were previously marked positive despite failed run status are
quarantined and excluded from normal training.

## Split

Group-aware split fields:

- scenario family
- map
- route hash
- seed

D3 Wave1 has zero new source text and zero new scenario IDs relative to
D2 v1.1, so this release must not be interpreted as template-disjoint or
scenario-disjoint generalization evaluation.

## Usage

A3 may extend its existing training/development view with
`train_addition.jsonl` and `val_addition.jsonl`.

`hard_negative_addition.jsonl` is a separate hard-case pool.

Existing D2 reserved/test candidates remain excluded from A3 tuning.

## Next acquisition

D3 Wave2 targets new source-text templates, new scenario IDs, safety
generalization, Town03_Opt probing, multi-step capability probing, and
held-out B2 generalization groups.
