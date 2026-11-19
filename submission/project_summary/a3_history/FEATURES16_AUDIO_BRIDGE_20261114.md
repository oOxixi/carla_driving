# Features16 competition rehearsal: voice evidence and pairing gap

On tiaozhansai, the repository `evaluate_voice_audio.py` completed all
250 existing labeled recordings (50 each in five language groups) using
SenseVoiceSmall + LoRA, FSMN-VAD and the existing NLU. A separate dependency
directory used the existing CUDA Torch runtime; the production environment
was not edited. Whisper cascade was disabled in this run. No digital or
physical noise was added. This is a historical, audio-only development
replay, not new independent evidence or the official deployment stack.

| Measure | Result |
| --- | ---: |
| Inference success | 250/250 |
| Normalized exact transcript | 239/250 (95.60%) |
| Character accuracy | 99.2445% |
| Intent | 249/250 (99.60%) |
| Slots (existing evaluator's all-sample denominator) | 248/250 (99.20%) |
| ASR stage latency, mean / P95 | 85.589 / 92.520 ms |
| ASR+NLU, P95 | 105.170 ms |

41 requests did require confirmation according to the observed command
records; intent accuracy is not the rate of commands executed.

Normalized reference-text joins found zero matches against the 850
historical multimodal planning cases and the two speed development
suites (128 + 80). No audio has been assigned by intent-only match,
no existing labels have been rewritten, and neither the audio nor
planning accuracy is a combined competition accuracy.

Fast path: if the official synchronized package is available, use it
unchanged. Otherwise schedule a new synchronized rehearsal: choose the
audio/scene pairings and expected actions before running any model,
capture RGB/state for each real command at a defined event, and record
audio, frame, state, reference labels, exclusions and scoring identity.
Use one shared ASR run (same transcript per Teacher/FP32/Features16)
and separately report ASR, application alignment and relative decay.
Do not use Teacher agreement as independent ground truth.

Evidence: `artifacts/numeric_speed_conditioned_20261112/asr_clean_250_primary_only.json`
(SHA256 `0b57e693e2e7c3084bdc4552cd624731ef8bddd9c83f245314aea970a9066a00`).
Audio reference manifest SHA256
`aa6eea1ffacc97b72f226887929c2bd70cf489be1fe12af87d7c6a8a020fffad`.
