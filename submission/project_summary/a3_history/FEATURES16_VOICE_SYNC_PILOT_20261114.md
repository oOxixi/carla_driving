# Town03_Opt synchronized voice pilot

A real historical Mandarin recording drove a new CARLA episode. Its audio
hash, reference transcript, SET_SPEED=30 km/h label, admissibility rule and
±2 km/h tolerance were declared in `voice_sync_pilot_reference.json` before
running. The reused audio makes this a development pilot, not a holdout.

The existing runner recorded fresh ASR output and created the Qwen request
after sensor warmup. The accepted speed limits were both 30 km/h and no
stop was required. The command record, request, RGB file and vehicle-state
frame were joined on command ID and CARLA frame 262; scene and frame
simulation timestamps matched. The same request and hash-bound RGB file
were replayed through FP32 and Features16 inside OpenExplorer.

| Arm | SET_SPEED plan | Predicted target | Reference match |
| --- | --- | ---: | --- |
| Qwen3.5-2B Teacher (live) | yes | 30.00 km/h | yes |
| Numeric Student FP32 (replay) | yes | 29.63 km/h | yes |
| Features16 BC (replay) | yes | 29.76 km/h | yes |

Exact transcript: “速度设为30公里。” The 240-frame CARLA run completed with
no collisions or lane invasions and the Teacher SET_SPEED step succeeded.
The internal temporary Qwen-wait command has its own terminal record and
was not counted as a second spoken command. The two Student arms were
not executed as closed loops. This is not a three-arm driving result,
latency qualification, or competition accuracy estimate.

The isolated ASR used SenseVoice+LoRA with VAD, and Whisper cascade off.
Teacher used the fixed model snapshot and adapter checkout, on vLLM
0.26.0 rather than the recorded formal serving stack. The launcher is
`run_voice_sync_pilot.sh`; it does not modify production endpoints.
Isolated listeners were closed after the run.

Raw logs and receipt: `artifacts/numeric_speed_conditioned_20261112/voice_sync_run.dvt7XvY0/`.
`three_way_sync_pilot.json` SHA256:
`d9311e1249717ad52fa1ee39ffa84cbef215f62bb54e19571ddf955322ba4cca`.

Next: predeclare several new audio/scene pairs with independent
references, including multi-step instructions and cases where the
scene constrains the action. Keep ineligible or failed captures visible
and separate the Student planning replay from Student closed-loop runs.
