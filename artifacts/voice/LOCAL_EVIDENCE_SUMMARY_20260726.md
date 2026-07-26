# Local voice evidence summary — 2026-07-26

This file distinguishes measured results from evidence that still needs an
external setup. Do not relabel the synthetic result as a 50 dBA result.

## Completed on the local RTX 5060 Laptop GPU

- Clean 250-file audio inference:
  - ASR exact accuracy: 95.60%
  - ASR character accuracy: 99.2445%
  - intent accuracy: 99.60%
  - slot accuracy: 99.20%
  - total latency: mean 91.32 ms, P95 109 ms, P99/max 172 ms
  - evidence: `local_clean_250_final_20260726.json`
- Deterministic synthetic white-noise stress test, 10 dB SNR, 250 files:
  - ASR exact accuracy: 94.40%
  - ASR character accuracy: 98.9698%
  - intent accuracy: 97.60%
  - slot accuracy: 98.80%
  - total latency: mean 87.00 ms, P95 94 ms, P99 156 ms, max 157 ms
  - evidence: `local_synthetic_snr10_250_20260726.json`
  - this is a digital SNR test, **not** official 50 dBA evidence
- Perturbation-consistency diagnostic:
  - 241/250 original transcripts were exact
  - 6/9 incorrect transcripts remained fully stable
  - 3 correct transcripts were unstable
  - therefore consistency is not used as a confidence score
  - evidence: `asr_consistency_20260726.json`
- Automated repository tests: 361 passed, 1 skipped.

## Still requires external evidence

- Formal 50 dBA evaluation requires calibrated acoustic playback/recording,
  a sound-level meter reading in the 49–51 dBA range, and the calibration log.
- The current SenseVoice/FunASR response exposes no calibrated utterance
  confidence, so measured confidence coverage is 0%. The parser safely blocks
  an explicitly low score when a backend provides one. Raw CTC posterior and
  transcript consistency were tested and rejected as misleading substitutes.
- The 250-file manifest audio is synthesized speech. It is real model
  inference over real audio files, but it must not be described as recordings
  from human speakers.
