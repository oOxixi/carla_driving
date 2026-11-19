# Qwen3.5-2B RTX 3090 local profile

This profile is intentionally isolated from the existing 7B installation and
is not a GitHub release result.

## Local paths

- Code: `/home/tiaozhansai/carla-driving-2B`
- Branch: `candidate-2b-cu130`
- Environment: `.venv-qwen2b-cu130`
- Model: `models/Qwen3.5-2B`
- Runtime: PyTorch 2.11.0 + CUDA 13.0, vLLM 0.26.0
- GPU: RTX 3090, selected with `QWEN_GPU_INDEX=0`

The 7B code, environment, and model are under the separate
`/home/tiaozhansai/carla-driving-7B` directory.

## Start

```bash
cd /home/tiaozhansai/carla-driving-2B
nohup env QWEN_GPU_INDEX=0 bash tools/run_qwen35_vllm_3090.sh \
  > artifacts/B_role_validation/qwen35_2b_3090_service.log 2>&1 < /dev/null &
echo $! > artifacts/B_role_validation/qwen35_2b_3090_service.pid
```

## Validate

```bash
.venv-qwen2b-cu130/bin/python -m tools.run_qwen_latency_gate \
  --base-url http://127.0.0.1:8000/v1 \
  --model Qwen/Qwen3.5-2B \
  --model-revision 15852e8c16360a2fea060d615a32b45270f8a8fc \
  --image artifacts/qwen_carla_closed_loop_0727/run_003/media/rgb_00140499.png \
  --output artifacts/B_role_validation/qwen35_2b_3090_latency_gate.json
```

The first real run on 2026-08-03 passed the 300 ms gate with P95 98.710 ms.
This is an RTX 3090 result and must not be labelled as A800 evidence.
