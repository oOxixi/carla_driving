# B1 D3 Wave2 Safe-Short Additive Release

Dataset version: `b1_d3_wave2_safe_short_v1`.

This release contains **374 strict-positive samples** from the
historical D3 Wave2 safe-short execution:

- A01: 114
- A06: 114
- CX01: 146

The entire historical CX02 family (125 runs) is intentionally
excluded.  CX02 was later root-cause diagnosed and fixed; those old
raw runs remain immutable and are not relabeled.

Teacher execution identity:

- profile: `b1-pinned-teacher-v4-wave2-scenario-sync-v1`
- git SHA: `252984d37e49ddc11eaddcde2bfb26d0d6f2086b`
- model: `Qwen/Qwen3.5-2B`
- revision: `15852e8c16360a2fea060d615a32b45270f8a8fc`

This is an additive training/development release.  It does not replace
D2 v1.1 or D3 Wave1.

The raw source artifact is immutable.
