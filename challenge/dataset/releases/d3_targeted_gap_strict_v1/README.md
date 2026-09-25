# B1 D3 Targeted Gap Strict Additive Release

Dataset version: `b1_d3_targeted_gap_strict_v1`.

This release contains **660 strict-positive command-level samples**
derived from **280 strict-positive closed-loop runs** selected from
the frozen 500-run targeted coverage-gap acquisition.

Published sample families:

- TC_E01: 120
- TC_F01: 450
- ACC_C04: 20
- SUP_C07: 20
- TC_G01: 50

Source acquisition:

- total terminal runs: 500
- strict-positive runs: 280
- excluded/non-positive runs: 220
- canonical rejected samples: 0

All 660 source RGB assets were integrity checked before publication.
Train/validation splitting is group-aware so samples from one
closed-loop run remain in one split.

The 220 excluded historical runs remain immutable. They are not
relabeled after later fixes; any recovery must use a new cohort.

This is an additive training/development release and does not replace
D2 v1.1, D3 Wave1, or D3 Wave2.
