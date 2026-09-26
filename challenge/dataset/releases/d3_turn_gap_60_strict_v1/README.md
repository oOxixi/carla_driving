# B1 D3 TURN Gap Strict Additive Release

Dataset version: `b1_d3_turn_gap_60_strict_v1`

This additive release contains **200 strict-positive command-level
Teacher samples** derived from **60/60 strict-pass closed-loop runs**.

Coverage:

- C01 KEEP_LANE -> TURN_LEFT -> SET_SPEED: 60 samples / 20 runs
- C02 YIELD -> TURN_LEFT -> SET_SPEED: 60 samples / 20 runs
- C03 FOLLOW -> SLOW_DOWN -> TURN_LEFT -> KEEP_LANE: 80 samples / 20 runs

Acquisition Git SHA:

`c7ecadf5ce1da1dd569681c458ccc09959c0b5d1`

Teacher:

- model: `Qwen/Qwen3.5-2B`
- revision: `15852e8c16360a2fea060d615a32b45270f8a8fc`
- artifact SHA256: `4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`
- mode: `planner_v2`

Canonicalization:

- collector commit: `912989f5bab4a864136f3774515e7cbd28e8dc24`
- collector SHA256: `792528d5564130ed8982f552e1207e3fa97eaaea3b992cdaaeea0370de002485`

The earlier five-seed validation/smoke runs are not included.
This release is additive and does not mutate any previously frozen release.
