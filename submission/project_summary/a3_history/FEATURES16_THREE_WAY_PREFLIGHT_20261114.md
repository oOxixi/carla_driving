# Features16 three-way preflight

## Scope and frozen inputs

This is a development transport check, not a competition benchmark.
It uses the first existing probe per family (compound, follow, set, slow)
from the controlled development suite, chosen without reading any new
predictions. The source case-file SHA256 is
`22730c8a036dc3f933c545731c2b27188d852b939cf2a875dd3d82b2f0a7ad3d`.
Each of the four requests and RGB files has an identity in the receipts.
Transport rewrites the RGB path without changing its bytes. The Teacher
client refreshes the deadline while retaining the original TTL.

## Results and failure isolation

- Numeric FP32 and Features16 BC in OpenExplorer returned four valid
  plans each. Their frozen artifact hashes are in the Student receipt.
- The existing Teacher endpoint reported READY, but initially rejected
  absolute RGB paths. Hash-verifying copies under its configured image
  root and sending relative references resolved the path-stage error.
  The requests then failed because the configured local vLLM port 8000
  refused connections. A readiness response alone is not inference proof.
- The pinned Teacher adapter commit `95e97b00` was checked out in an
  isolated server worktree. The smoke uses the previously fingerprinted
  Qwen3.5-2B snapshot and the available vLLM 0.26.0/CUDA 13.0 stack, not
  the recorded frozen serving stack. The original endpoint was not
  restarted or reconfigured.
- The first isolated inference hit the original two-second deadline
  during cold initialization, and three following calls were rejected
  by the single-request concurrency limit. With separate warmup and
  waiting for the prior request to finish, all four measured requests
  returned schema-valid plans under the unchanged two-second fixture
  TTL. No relaxed-TTL evaluation retry was needed. The outer SSH
  shell returned 127 due to a trailing CR after the receipt was written;
  the complete receipt was independently checked, as were the original
  endpoint and the cleanup of both isolated ports.
- Same-source request and RGB hashes match across the receipts:
  `teacher_isolated_warm_smoke.json` SHA256
  `adddd6ddf1d6277cca3aec5c702aa0f00dea5e6ab9f35c6233b35088bf3e9c83`;
  `three_way_student_transport_smoke.json` SHA256
  `a2d5151b08f547150d618247fae40024a7922a439fc47a99b1bece6660505606`.

## Formal prerequisites

No official 1000-frame benchmark package was located in the inspected
project materials, release attachment locations or public search. This
does not establish that it was never distributed. If supplied, record
its provenance and freeze data identity and scoring before inference.
Otherwise use a newly collected, audited set with audio, RGB, vehicle
state, source/label provenance, and exclusions against training,
development, calibration and previously exposed evaluation.

The old prospective acquisition configuration provides a scoring
policy but no collected case manifest and is bound to the older
candidate. It is not an audio-inclusive competition result. Before a
formal run, bind the actual serving and candidate identities and
freeze reference labels, the denominator/failure policy and assets.
Run the Teacher, numeric FP32 and deployment version on identical
inputs, reporting each application's metric and relative decay. The
four transport fixtures cannot be promoted to that evaluation.
