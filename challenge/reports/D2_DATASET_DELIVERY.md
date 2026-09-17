# B1 D2 Dataset Delivery Record

## 1. Scope

This document records the completion state and delivery contract for **B1 / D2 Teacher dataset and data governance**.

According to the challenge sprint plan, D2 requires:

- continued Teacher acquisition from Seen / Variant / Unseen sources;
- deduplication and multimodal alignment checks;
- an initial Train / Val split;
- Test candidates isolated from Student tuning;
- cumulative valid Teacher samples reaching approximately 3,000–5,000.

The final frozen Dataset v1 requirements (8k–15k Train, frozen Test, Calibration 300–500, and official-like 1000) belong to **D3**, not D2.

---

## 2. Final D2 Code Version

```text
FINAL_D2_GIT_SHA
60463c20b32bed51017a4bd24b79da86792b316e
```

Branch used during D2 completion:

```text
fix/teacher-v4-semantic-sync
```

Teacher v4:

```text
teacher_profile = b1-pinned-teacher-v4
teacher_git_sha = 95e97b00def8ec36f12937da34ce8bb9082c4a04
teacher_model   = Qwen/Qwen3.5-2B
qwen_mode       = planner_v2
```

Wave2 plan provenance:

```text
plan_version          = b1_d2_expansion_wave2_v1
plan_repo_git_sha     = a5b0258eb3d2d184f053e62b5c382741217259d3
plan_file_sha256      = 28bccc35cc76483b4d7bcfe4c989238eaabc147b99de399cfbdd439e9467a819
plan_canonical_sha256 = c20e997494c67f9238a200e359b81abcd5b7b51aaf365a8d16e7f60ebfddaea8
```

Wave2 collector:

```text
collector_git_sha = 444d97cea3a76f6b55a6524a52b0302febde223c
collector_sha256  = 72a630db45d141ec417f2e33912a62e168ca975bcf5ef9f1434e135397f37e49
dataset_version   = teacher_distill_v0.4_d2_expansion_wave2_v4
```

---

## 3. D2 Acquisition Result

### D2 Wave2

```text
planned runs       = 2000
executed runs      = 2000
runner succeeded   = 2000
runner failed      = 0

valid samples      = 2461
rejected samples   = 0
positive samples   = 2320
hard negatives     = 141
unique group keys  = 2000
```

Wave2 acquisition freeze:

```text
freeze_status = PASS
freeze_manifest_sha256 =
81579e4fb393c1daf4fc4ca678454e8969c5c0aa9d2171a273be6f28c294b64c
```

Wave2 data hashes:

```text
d2_valid_jsonl =
3d3fdf973865c18e21d341ed5360fb0275f39ca0a3107b7197f3bbcf707db961

d2_rejected_jsonl =
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

provenance_manifest =
3931262733107822e7d6648f4db99d9399c8df36713f5e32a101c9a34d195fec

run_state =
0cd19f5658211762c4f14f8ef60fe2e360602b7d3096d9f223339b11d9f45899
```

Wave2 integrity:

```text
visual_input_count       = 2461
missing_visual_inputs    = 0
visual_sha256_mismatch   = 0
visual_size_mismatch     = 0

log_jsonl_count          = 2000
log_summary_count        = 2000
log_pair_count           = 2000

NO_CANONICAL_SUBMIT      = 0
ROUTE_UNREACHABLE        = 0
distance_contract        = 0
```

Hard-negative reasons:

```text
CLOSED_LOOP_COLLISION                         65
SAFETY_OVERRIDE_TERMINAL                      25
SCENARIO_ACCEPTANCE_FAILED                    28
TEACHER_EXECUTION_NOT_SUCCEEDED:RUNTIME_ENDED  4
TEACHER_EXECUTION_NOT_SUCCEEDED:STEP_TIMEOUT  19
------------------------------------------------
TOTAL                                         141
```

---

## 4. Cumulative D2 Governance

Historical data:

```text
D1 raw             = 133
D2 Wave1 raw       = 1198
D2 Wave2 raw       = 2461
--------------------------------
D2 cumulative raw  = 3792
```

Final governed assets:

```text
raw samples                 = 3792
historical excluded         = 192
governed assets             = 3600

positive eligible           = 3395
hard-negative eligible      = 205
```

Historical exclusions remain immutable:

```text
historical directional semantic quarantine = 189
D1 legacy hold                              = 3
------------------------------------------------
total excluded                              = 192
```

Wave2 Teacher-v4 directional semantic audit:

```text
unexpected directional states = 0
status                        = PASS
```

Governance canonical SHA256:

```text
674f573e5c4d93268c5cee7144a05d613651b822202fcffc2ee48158cabb2edd
```

Final governance report file SHA256:

```text
49310a3b8b6a8dea7b14c074049e8d1ac4674da253c836091e8a0ffb8f93ce9f
```

---

## 5. D2 Provisional Group-Aware Split

Split unit:

```text
scenario family + map + route + seed / group_key
```

Adjacent-frame random splitting is forbidden.

Final D2 provisional split:

| Split | Samples | Groups | Positive | Hard Negative | Ratio |
|---|---:|---:|---:|---:|---:|
| Train | 2520 | 1818 | 2377 | 143 | 70% |
| Val | 540 | 540 | 509 | 31 | 15% |
| Reserved Test Candidate | 540 | 540 | 509 | 31 | 15% |
| **Total** | **3600** | **2898 unique groups** | **3395** | **205** | **100%** |

Hard Gates:

```text
sample overlap              = 0
group overlap               = 0
historical exclusion leak   = 0
split ratio deviation       = 0
training role preserved     = PASS
```

Canonical hashes:

```text
split_report_canonical_sha256 =
e0990a04fbb5383e28bf1cea59b99ef39f2d190bdcf319442dd3da66b53a3094

split_manifest_canonical_sha256 =
5c5119b645622c0e52d60e84f64e0d2d6e1c414c1fe4c3e733e26ac3ff2ae757
```

Artifact hashes:

```text
train.jsonl =
8f4cdc6c764416f0376eae8281025c8f138dcc776bdd9ca92666299ec739c019

val.jsonl =
a13263c0019b65866a41b471e5e784c49588a3a2648854bff48655ff7fc3668d

reserved_test_candidates.jsonl =
28987e807a612335d7485e7295cce7df6812225a8778f8477c60ee08437df3bc

split_assignments.jsonl =
6cf3a000808ac474ea190dfed8171cc97c56edae738a3be5f24d3ad78c4b28a7

split_report.json =
4890cef17c3b2ab4d8414792aac9fb8ba572fca908e1b503a2fe0350e4034c34

split_manifest.json =
81f86e39a06b8b465544e122165b6e61c9c18db3471f6a24a64a6e1232ffaff1
```

---

## 6. D2 Gates

```text
D2_WAVE2_ACQUISITION_FREEZE = PASS
D2_RAW_SIZE_GATE_3000_5000  = PASS
D2_CUMULATIVE_GOVERNANCE    = PASS
D2_PROVISIONAL_SPLIT         = PASS
D2_FINAL_DATA_GATE           = PASS
D2_FINAL_DELIVERY_GATE       = PASS
```

Git worktree at final delivery:

```text
clean
```

---

## 7. Files That Belong in Git

The following D2 code should be tracked in Git:

```text
challenge/dataset/build_d2_expansion_plan.py
challenge/dataset/tests/test_d2_expansion_plan.py

challenge/dataset/build_d2_wave2_plan.py
challenge/dataset/tests/test_d2_wave2_plan.py

challenge/dataset/collect_d2_wave2.py
challenge/dataset/tests/test_d2_wave2_collector.py

challenge/dataset/build_semantic_governance_v4.py
challenge/dataset/build_training_eligibility_v4.py

challenge/dataset/build_d2_wave2_freeze.py
challenge/dataset/build_d2_cumulative_governance_v5.py
challenge/dataset/build_d2_split_v1.py
```

The D2 delivery record itself should be tracked as:

```text
challenge/reports/D2_DATASET_DELIVERY.md
```

---

## 8. Large Artifacts Are Not Normal Git Source Files

The Wave2 acquisition root is approximately 5.46 GiB:

```text
artifacts/b1_d2_wave2_2000_teacher_v4/
```

Do **not** force-add the complete raw image/log acquisition directory into normal Git history.

Keep the raw acquisition directory on the server as the immutable data source and preserve its manifests/hashes.

The important server-side artifact roots are:

```text
artifacts/b1_d2_wave2_2000_teacher_v4/
artifacts/b1_d2_cumulative_governance_v5/
artifacts/b1_d2_split_v1/
artifacts/b1_training_eligibility_v4/
artifacts/b1_semantic_governance_v4/
```

Before D3, preserve these directories and do not delete or overwrite them.

If the project later requires dataset binaries to be distributed remotely, use the team's approved dataset/object-storage mechanism rather than normal Git history.

---

## 9. Verify Which D2 Files Are Actually Tracked

Run:

```bash
git ls-files \
  'challenge/dataset/*d2*' \
  'challenge/dataset/*governance*' \
  'challenge/reports/D2_DATASET_DELIVERY.md'
```

Check whether artifacts are ignored:

```bash
git check-ignore -v \
  artifacts/b1_d2_wave2_2000_teacher_v4/freeze_manifest.json \
  artifacts/b1_d2_cumulative_governance_v5/d2_cumulative_governance_report.json \
  artifacts/b1_d2_split_v1/split_manifest.json \
  artifacts/b1_d2_split_v1/train.jsonl
```

Do not use `git add -f` on the 5.46 GiB raw acquisition root.

---

## 10. D2 / D3 Boundary

D2 is complete at the **provisional dataset** stage:

```text
cumulative Teacher assets: 3000–5000 target reached
initial Train / Val split: complete
Test candidates isolated: complete
```

D3 is responsible for freezing Dataset v1:

```text
Train valid Teacher samples: 8k–15k target
Val: isolated by scenario / route / seed
Test: frozen
Calibration: 300–500
Official-like: 1000
```

Therefore:

- `reserved_test_candidates.jsonl` is **not yet the final frozen D3 test set**.
- D2 data remains part of the cumulative D3 dataset pool.
- D3 expansion must not leak reserved groups into Train.
- Historical 189 contaminated directional samples remain permanently quarantined.
- D1/D2 seeds must not be reused by D3 acquisition.

---

## 11. D2 Final Status

```text
B1_D2_STATUS = COMPLETE
FINAL_D2_GIT_SHA = 60463c20b32bed51017a4bd24b79da86792b316e
D2_FINAL_DELIVERY_GATE = PASS
```

The next phase is **D3 Dataset v1 expansion and freeze**.
