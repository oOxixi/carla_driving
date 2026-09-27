# B1 D3 Gap300 Strict Additive Release

Dataset version: `b1_d3_gap300_strict_v1`.

This release contains **820 strict-positive command-level samples**
derived from **280 strict-positive closed-loop runs** selected from
the frozen 300-run Gap300 acquisition.

Published sample families:

- D01: 50
- C01: 225
- C02: 225
- C03: 320

Source acquisition:

- attempted runs: 300
- strict-positive runs: 280
- excluded runs: 20
- canonical rejected samples: 0

All 820 source RGB assets were integrity checked before publication.
Train/validation splitting is deterministic and group-aware so all
command-level samples from one closed-loop run remain in one split.

The 20 excluded C03 mod5=4 historical runs remain immutable. They
are not relabeled as positive or hard-negative evidence.

This is an additive training/development release and does not replace
D2 v1.1 or any prior D3 additive release.
