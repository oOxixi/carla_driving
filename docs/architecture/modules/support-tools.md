# Complete support command index

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [维护工具的运行上下文和证据范围](../functions/environment-delivery.md)

Parent: [Support module](../modules/support.md). This inventory covers every script in tools/, scripts/, docker/scripts/, docker/entrypoints/ and both benchmark tools directories at audit time. Parameters below are statically discovered option names; source argparse/PowerShell/bash parsing owns defaults, required combinations and behavior. Presence in this index is not an execution-success claim.

## Contract and execution rules

Each command consumes CLI/environment parameters plus the referenced scenario/model/data/report files. Validate those source files against their owning function page before invoking. Generators and execution commands can write artifacts, create simulator actors, load GPU models, start services or update reference evidence; verification tools generally read their specified inputs and may emit reports. Review destination flags before execution. Nonzero exit, missing external assets or incomplete evidence must remain visible.

Python CLI help: python tools/NAME.py --help; review shell/PowerShell source before use because not every wrapper implements help safely. Run relevant integration/voice/qwen tests for changed helpers, and real GPU/CARLA validation for runtime claims. Renaming a command requires updating runbooks, parent launchers, Docker calls, tests and artifact/evidence consumers. Changing report fields requires updating schema/scorecard/index readers.

## Voice and audio

| Source | Function description | Discovered options |
|---|---|---|
| [analyze_asr_consistency.py](../../../tools/analyze_asr_consistency.py) | Evaluate whether perturbation consistency is usable as ASR confidence. | `--output`, `--limit`, `--seed`, `--noise-ratio` |
| [calibrate_whisper_confidence.py](../../../tools/calibrate_whisper_confidence.py) | Fit and evaluate a provisional faster-whisper confidence calibration. | `--manifest`, `--output`, `--evidence`, `--model`, `--device`, `--compute-type`, `--languages`, `--include-snr-db`, `--seed`, `--limit` |
| [evaluate_saved_asr_nlu.py](../../../tools/evaluate_saved_asr_nlu.py) | Re-evaluate saved ASR transcripts through the current NLU implementation. | `--failures`, `--warmup`, `--latency-samples` |
| [evaluate_voice_audio.py](../../../tools/evaluate_voice_audio.py) | Run the complete voice pipeline over a manifest and write audit evidence. | `--porcelain`, `--manifest`, `--audio-root`, `--condition`, `--noise-level-dba`, `--calibration-log`, `--synthetic-snr-db`, `--noise-seed`, `--output`, `--limit`, `--min-intent-accuracy` |
| [export_group1_sensevoice_onnx_static.py](../../../tools/export_group1_sensevoice_onnx_static.py) | Export a fixed-shape SenseVoice ONNX for TensorRT benchmarking. | `--model`, `--lora-dir`, `--output-dir`, `--device`, `--frames`, `--opset-version`, `--language-id`, `--textnorm-id` |
| [prepare_group1_voice_dataset.py](../../../tools/prepare_group1_voice_dataset.py) | Prepare the official Group 1 voice dataset for task 5/6 evaluation. | `--porcelain`, `--zip-path`, `--extract-root`, `--output-root`, `--official-for-group1-tasks` |
| [run_group1_voice_onnx_benchmark.py](../../../tools/run_group1_voice_onnx_benchmark.py) | Benchmark the exported SenseVoice ONNX model on Group 1 voice data. | `--porcelain`, `--manifest`, `--audio-root`, `--onnx-model`, `--base-model`, `--output`, `--provider`, `--language`, `--use-itn`, `--limit`, `--warmup`, `--latency-samples` |
| [run_group1_voice_text_regression.py](../../../tools/run_group1_voice_text_regression.py) | Run deterministic Group 1 task 5 NLU/safety regression from a voice manifest. | `--porcelain`, `--manifest`, `--output`, `--asr-confidence`, `--low-asr-confidence`, `--min-intent-accuracy`, `--min-slot-accuracy`, `--limit` |
| [synthesize_stress_audio.py](../../../tools/synthesize_stress_audio.py) | Generate deterministic Chinese TTS audio references for full-chain testing. | `--cases-file`, `--voice`, `--rate` |
| [verify_voice_weights.py](../../../tools/verify_voice_weights.py) | Command-line entry point; inspect source help before execution. | See source / wrapper parameters |

## Qwen, perception and multimodal data

| Source | Function description | Discovered options |
|---|---|---|
| [benchmark_audit.py](../../../tools/benchmark_audit.py) | Command-line entry point; inspect source help before execution. | `--write-checksum`, `--checksum` |
| [benchmark_perception_pipeline.py](../../../tools/benchmark_perception_pipeline.py) | Benchmark C synchronization/fusion with deterministic synthetic observations. | `--output`, `--frames` |
| [build_basic_track_scorecard.py](../../../tools/build_basic_track_scorecard.py) | Merge CARLA/Qwen and real-audio reports into the four promotion gates. | `--carla-report`, `--voice-report`, `--output` |
| [build_detector_miss_supplement.py](../../../tools/build_detector_miss_supplement.py) | Correct detector-miss cases so every explicit semantic match is removed. | `--output` |
| [build_four_modal_cases_v2.py](../../../tools/build_four_modal_cases_v2.py) | Build an unambiguous v2 manifest while reusing immutable RGB/LiDAR files. | `--output` |
| [build_multimodal_dataset.py](../../../tools/build_multimodal_dataset.py) | Build schema-v1 multimodal JSONL files from normalized capture records. | `--dataset-root`, `--output-root`, `--sequence-id`, `--scenario-id`, `--seed`, `--difficulty`, `--map`, `--git-commit`, `--config-sha256`, `--model`, `--model-version` |
| [build_qwen_four_modal_stress_set.py](../../../tools/build_qwen_four_modal_stress_set.py) | Build an auditable four-modal Qwen stress set from real CARLA captures. | `--collection-dir`, `--output-dir` |
| [capture_qwen_test_image.py](../../../tools/capture_qwen_test_image.py) | Command-line entry point; inspect source help before execution. | `--host`, `--port`, `--timeout-s`, `--map`, `--spawn-index`, `--output`, `--width`, `--height`, `--fov`, `--map-warmup-frames`, `--sensor-warmup-frames`, `--lead-distance-m` |
| [collect_qwen_target_scenes.py](../../../tools/collect_qwen_target_scenes.py) | Collect real CARLA RGB frames with deterministic multi-vehicle annotations. | `--host`, `--port`, `--output-dir`, `--seeds`, `--width`, `--height`, `--fov`, `--weather-profiles`, `--pedestrian-seeds`, `--occlusion-seeds`, `--dense-target-count` |
| [finalize_four_modal_report.py](../../../tools/finalize_four_modal_report.py) | Recompute four-modal metrics from an already completed real-model run. | `--output` |
| [four_modal_metrics.py](../../../tools/four_modal_metrics.py) | Metric policy for the four-modal real-model benchmark. | See source / wrapper parameters |
| [frozen_text_hash.py](../../../tools/frozen_text_hash.py) | Stable checksums for frozen, text-only validation artifacts. | See source / wrapper parameters |
| [promote_reference_run.py](../../../tools/promote_reference_run.py) | Promote one completed, hash-verified runtime directory to reference evidence. | `--run-dir`, `--destination`, `--hardware-label` |
| [qwen_remote_smoke.py](../../../tools/qwen_remote_smoke.py) | Command-line entry point; inspect source help before execution. | See source / wrapper parameters |
| [run_four_modal_full_chain.py](../../../tools/run_four_modal_full_chain.py) | Evaluate frozen full-chain latency with separate accuracy input contracts. | `--model-path`, `--qwen-base-url`, `--profile`, `--asr-manifest`, `--multimodal-cases`, `--latency-manifest`, `--warmup`, `--measured`, `--diagnostic`, `--scenario-completion-rate`, `--hardware-label`, `--output` |
| [run_qwen_batch_benchmark.py](../../../tools/run_qwen_batch_benchmark.py) | Run a frozen proxy set through one loaded local Qwen2.5-VL checkpoint. | `--model-path`, `--image`, `--image-root`, `--output`, `--max-new-tokens`, `--awq-backend` |
| [run_qwen_carla_closed_loop.py](../../../tools/run_qwen_carla_closed_loop.py) | Run one auditable RGB/LiDAR -> Qwen -> A/B/C/D -> CARLA loop. | `--host`, `--port`, `--expected-map`, `--model-path`, `--output-dir`, `--command`, `--frames`, `--fixed-delta`, `--sensor-timeout`, `--target-speed-mps`, `--media-stride`, `--sensor-profile`, `--max-new-tokens`, `--awq-backend` |
| [run_qwen_expanded_instruction_benchmark.py](../../../tools/run_qwen_expanded_instruction_benchmark.py) | Evaluate Qwen on the frozen expanded CARLA language benchmark. | `--dataset`, `--base-url`, `--model`, `--output`, `--records-output`, `--category`, `--sample-per-category`, `--limit`, `--concurrency`, `--timeout-s`, `--retries`, `--progress-every`, `--max-incorrect-examples`, `--server-gpu-name`, `--server-gpu-memory-mib` |
| [run_qwen_latency_gate.py](../../../tools/run_qwen_latency_gate.py) | Run only the Qwen-VL latency gate; never starts a correctness suite. | `--base-url`, `--model`, `--model-revision`, `--image`, `--output`, `--warmups`, `--measurements`, `--threshold-ms`, `--timeout-s`, `--inference-gpu-name`, `--inference-gpu-memory-mib`, `--inference-gpu-source` |
| [run_qwen_vl_decision.py](../../../tools/run_qwen_vl_decision.py) | Run one strict high-level decision with a local Qwen2.5-VL checkpoint. | `--model-path`, `--image-root`, `--max-new-tokens`, `--awq-backend`, `--output` |
| [validate_c_role.py](../../../tools/validate_c_role.py) | Generate member C's deterministic pre-CARLA acceptance evidence. | `--output-dir` |
| [validate_four_modal_dataset.py](../../../tools/validate_four_modal_dataset.py) | Validate every four-modal manifest reference and split invariant. | `--cases-file`, `--output` |
| [validate_language_testset.py](../../../tools/validate_language_testset.py) | Validate the frozen Chinese driving-language proxy test set. | `--report` |
| [validate_multimodal_dataset.py](../../../tools/validate_multimodal_dataset.py) | Validate multimodal JSONL records without third-party dependencies. | `--dataset-root`, `--check-files` |
| [audit_global_benchmark_v1.py](../../../CARLA-Language-Benchmark/tools/audit_global_benchmark_v1.py) | Compatibility entry point for the repository-wide benchmark audit. | See source / wrapper parameters |
| [merge_carla_language_benchmark_v1.py](../../../CARLA-Language-Benchmark/tools/merge_carla_language_benchmark_v1.py) | Command-line entry point; inspect source help before execution. | See source / wrapper parameters |
| [normalize_carla_benchmark_schema_v1.py](../../../CARLA-Language-Benchmark/tools/normalize_carla_benchmark_schema_v1.py) | Command-line entry point; inspect source help before execution. | See source / wrapper parameters |
| [audit_global_benchmark_v1.py](../../../CARLA_Language_Benchmark/tools/audit_global_benchmark_v1.py) | Command-line entry point; inspect source help before execution. | See source / wrapper parameters |

## Scenario execution and control

| Source | Function description | Discovered options |
|---|---|---|
| [benchmark_control_runtime.py](../../../tools/benchmark_control_runtime.py) | Measure D validation and final safety arbitration without CARLA I/O. | `--output`, `--frames` |
| [build_acceptance_suite.py](../../../tools/build_acceptance_suite.py) | Build the 83-scenario Dongfeng-track acceptance suite. | `--check`, `--refresh-scenarios` |
| [check_sensor_stability.py](../../../tools/check_sensor_stability.py) | CLI entry point for the current-world CARLA sensor stability probe. | See source / wrapper parameters |
| [live_carla_viewer.py](../../../tools/live_carla_viewer.py) | Read-only CARLA chase camera with live command subtitles. | `--host`, `--carla-port`, `--http-port`, `--width`, `--height`, `--log-dir`, `--command-log`, `--scenario-id` |
| [probe_s2_route_anchor.py](../../../tools/probe_s2_route_anchor.py) | Probe Town spawn points against the S2 out-and-back lane-change profile. | `--host`, `--port`, `--map`, `--candidates`, `--sample-step-m`, `--sample-end-m`, `--inspect-location` |
| [replay_acceptance.py](../../../tools/replay_acceptance.py) | Run RGB/LiDAR/Qwen records through the offline A/B/C/D acceptance chain. | `--output`, `--rgb-detector-model`, `--confidence`, `--iou`, `--input-size` |
| [run_acceptance_suite_a800.py](../../../tools/run_acceptance_suite_a800.py) | Run all 83 scored acceptance scenarios once on the prepared A800 host. | `--project`, `--python`, `--output`, `--qwen-service-url`, `--qwen-image-root`, `--carla-host`, `--carla-port`, `--warmup-requests`, `--qwen-timeout-ms`, `--hardware`, `--cuda`, `--fail-fast`, `--skip-summary-root`, `--exclude-scenario-id`, `--include-scenario-id`, `--suite-revision`, `--host`, `--port`, `--scenario-file`, `--perception-mode`, `--scenario-facts-mode`, `--sensor-profile`, `--realtime`, `--qwen-mode`, `--qwen-queue-size`, `--qwen-image-prefix`, `--sensor-warmup-frames`, `--sensor-timeout-s`, `--print-every`, `--log-dir` |
| [run_carla_scenario_matrix.py](../../../tools/run_carla_scenario_matrix.py) | Repeat real-sensor CARLA scenarios across deterministic evidence seeds. | `--scenario`, `--seeds`, `--repeats-per-seed`, `--output-dir`, `--carla-pythonpath`, `--timeout-s`, `--host`, `--port`, `--scenario-facts-mode`, `--resume`, `--use-current-map`, `--scenario-file`, `--seed`, `--perception-mode`, `--sensor-profile`, `--sensor-timeout-s`, `--sensor-warmup-frames`, `--log-dir`, `--print-every` |
| [run_control_safety_benchmark.py](../../../tools/run_control_safety_benchmark.py) | Generate D's control/safety P95 latency acceptance evidence. | `--iterations`, `--warmup`, `--threshold-ms`, `--output` |
| [run_generalization_gate.py](../../../tools/run_generalization_gate.py) | Build and validate deterministic in-memory scenario perturbations. | `--matrix`, `--holdout`, `--kind`, `--output-dir`, `--max-per-scenario` |
| [run_long_stability.py](../../../tools/run_long_stability.py) | Run a wall-clock CARLA sensor soak with GPU and periodic Qwen evidence. | `--output`, `--duration-minutes`, `--host`, `--port`, `--gpu-index`, `--gpu-sample-seconds`, `--qwen-model`, `--qwen-base-url`, `--qwen-profile`, `--qwen-image-root`, `--qwen-image-ref`, `--qwen-interval-seconds`, `--qwen-timeout-budget-seconds` |
| [validate_control_generalization.py](../../../tools/validate_control_generalization.py) | CARLA-free numerical validation for the member-3 generalization policy. | See source / wrapper parameters |
| [validate_official_scenes.py](../../../tools/validate_official_scenes.py) | CARLA-independent contract checks for the three official competition scenes. | See source / wrapper parameters |
| [validate_route_generalization.py](../../../tools/validate_route_generalization.py) | Validate destination route planning against one or more live CARLA maps. | `--host`, `--port`, `--timeout-s`, `--maps`, `--pairs-per-map`, `--minimum-endpoint-gap-m`, `--minimum-route-length-m`, `--maximum-route-length-m`, `--maximum-junction-count`, `--required-profiles`, `--candidate-limit`, `--output` |
| [validate_s2_member3_evidence.py](../../../tools/validate_s2_member3_evidence.py) | Validate the member-3 S2 full-chain evidence bundle. | `--summary`, `--output`, `--functional-only` |
| [validate_s3_member4_evidence.py](../../../tools/validate_s3_member4_evidence.py) | Validate member-4 S3 emergency-chain evidence from a real CARLA run. | `--summary`, `--output`, `--functional-only` |
| [validate_scenarios.py](../../../tools/validate_scenarios.py) | Command-line entry point; inspect source help before execution. | See source / wrapper parameters |
| [fetch_scenario_runner.ps1](../../../scripts/fetch_scenario_runner.ps1) | Command-line entry point; inspect source help before execution. | See source / wrapper parameters |
| [run_official_s2_member3.sh](../../../scripts/run_official_s2_member3.sh) | Command-line entry point; inspect source help before execution. | `--validate`, `--smoke`, `--run` |
| [run_official_s3_member4.sh](../../../scripts/run_official_s3_member4.sh) | Command-line entry point; inspect source help before execution. | `--validate`, `--smoke`, `--run` |
| [run_official_scenes.ps1](../../../scripts/run_official_scenes.ps1) | Command-line entry point; inspect source help before execution. | `--host`, `--port`, `--timeout-s`, `--warmup-frames`, `--sensor-warmup-frames`, `--sensor-timeout-s`, `--perception-mode`, `--scenario-facts-mode`, `--follow-spectator`, `--realtime`, `--print-every`, `--log-dir`, `--qwen-service-url`, `--qwen-mode`, `--qwen-timeout-ms`, `--qwen-queue-size`, `--qwen-image-root`, `--qwen-image-prefix`, `--scenario-file`, `--max-frames` |
| [run_scenario_runner.ps1](../../../scripts/run_scenario_runner.ps1) | Command-line entry point; inspect source help before execution. | See source / wrapper parameters |

## Deployment and release

| Source | Function description | Discovered options |
|---|---|---|
| [build_submission_package.py](../../../tools/build_submission_package.py) | Check release inputs and render the raw-backed Qwen 2B reproduction guide. | `--root`, `--reference-run`, `--output` |
| [create_qwen_launch_logs.py](../../../tools/create_qwen_launch_logs.py) | Allocate fresh, private Qwen launch logs without reusing prior evidence. | `--output-root` |
| [generate_model_manifest.py](../../../tools/generate_model_manifest.py) | Generate per-file and aggregate SHA-256 metadata for a local model. | `--model-name`, `--license`, `--output` |
| [generate_source_manifest.py](../../../tools/generate_source_manifest.py) | Hash all tracked and untracked Python source files in the repository. | `--repo-root`, `--output`, `--others`, `--exclude-standard` |
| [generate_wheelhouse_lock.py](../../../tools/generate_wheelhouse_lock.py) | Turn one pip --report result into a strict wheelhouse manifest and hash lock. | `--report`, `--wheelhouse`, `--lock`, `--requirements-lock` |
| [repro_cli.py](../../../tools/repro_cli.py) | Container-side entry point for the independent reproduction package. | `--qwen-remote`, `--qwen-base-url`, `--qwen-model`, `--scenario-file`, `--sensor-profile`, `--perception-mode`, `--realtime`, `--log-dir`, `--profile`, `--asr-manifest`, `--multimodal-cases`, `--latency-manifest`, `--warmup`, `--measured`, `--hardware-label`, `--output`, `--duration-minutes`, `--host`, `--port`, `--qwen-profile`, `--qwen-image-root`, `--qwen-image-ref`, `--data-root`, `--output-root`, `--qwen-log`, `--carla-log`, `--evaluate-run` |
| [run_qwen3vl_2b_vllm_cu132.sh](../../../tools/run_qwen3vl_2b_vllm_cu132.sh) | Command-line entry point; inspect source help before execution. | See source / wrapper parameters |
| [verify_model_manifest.py](../../../tools/verify_model_manifest.py) | Verify that one staged model profile exactly matches its release manifest. | `--manifest`, `--root`, `--profile` |
| [verify_qwen_kernel.py](../../../tools/verify_qwen_kernel.py) | Strict parser for one Qwen GPTQ/Marlin launch evidence block. | See source / wrapper parameters |
| [verify_release_lock.py](../../../tools/verify_release_lock.py) | Verify one hashed staged release asset before it is consumed by a build. | `--lock`, `--root`, `--key` |
| [verify_vllm_cu132_inputs.py](../../../tools/verify_vllm_cu132_inputs.py) | Verify immutable release inputs before the offline CUDA 13.2 wheel build. | `--source`, `--source-lock`, `--wheelhouse`, `--wheelhouse-lock` |
| [verify_wheelhouse_lock.py](../../../tools/verify_wheelhouse_lock.py) | Reject any wheelhouse drift from its frozen complete manifest. | `--lock`, `--wheelhouse`, `--suffix` |
| [run_full_pipeline.sh](../../../scripts/run_full_pipeline.sh) | Command-line entry point; inspect source help before execution. | See source / wrapper parameters |
| [export-images.ps1](../../../docker/scripts/export-images.ps1) | Command-line entry point; inspect source help before execution. | See source / wrapper parameters |
| [verify-stack.ps1](../../../docker/scripts/verify-stack.ps1) | Command-line entry point; inspect source help before execution. | See source / wrapper parameters |
| [controller.sh](../../../docker/entrypoints/controller.sh) | Command-line entry point; inspect source help before execution. | See source / wrapper parameters |
| [qwen.sh](../../../docker/entrypoints/qwen.sh) | Command-line entry point; inspect source help before execution. | See source / wrapper parameters |



## 模块接口与参数核对（2026-09-20）

维护工具不是统一入口：tools/scripts/docker脚本及两套benchmark目录各有消费者。Python CLI参数见逐文件页的完整add_argument表，shell/PowerShell参数以源脚本为准。

### 参数语义与生效边界

参数表同时记录default/type/choices/required/action；省略default时由argparse/action决定，不能一律写None。工具可能读写产物、创建CARLA actor、启动服务或加载GPU；不得把脚本存在当已通过。

### 上下游与修改影响

改参数/报告字段需反查父启动器、Docker入口、runbook、Schema及报告消费者；保留返回码和原始输出。工作目录错误见AUDIT A06，工具检查通过不证明完整业务链正确。

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [scripts/fetch_scenario_runner.ps1](../functions/scripts--fetch_scenario_runner--ps1.md)
- [scripts/run_full_pipeline.sh](../functions/scripts--run_full_pipeline--sh.md)
- [scripts/run_official_s2_member3.sh](../functions/scripts--run_official_s2_member3--sh.md)
- [scripts/run_official_s3_member4.sh](../functions/scripts--run_official_s3_member4--sh.md)
- [scripts/run_official_scenes.ps1](../functions/scripts--run_official_scenes--ps1.md)
- [scripts/run_scenario_runner.ps1](../functions/scripts--run_scenario_runner--ps1.md)
- [tools/analyze_asr_consistency.py](../functions/tools--analyze_asr_consistency--py.md)
- [tools/benchmark_audit.py](../functions/tools--benchmark_audit--py.md)
- [tools/benchmark_control_runtime.py](../functions/tools--benchmark_control_runtime--py.md)
- [tools/benchmark_perception_pipeline.py](../functions/tools--benchmark_perception_pipeline--py.md)
- [tools/build_acceptance_suite.py](../functions/tools--build_acceptance_suite--py.md)
- [tools/build_basic_track_scorecard.py](../functions/tools--build_basic_track_scorecard--py.md)
- [tools/build_detector_miss_supplement.py](../functions/tools--build_detector_miss_supplement--py.md)
- [tools/build_four_modal_cases_v2.py](../functions/tools--build_four_modal_cases_v2--py.md)
- [tools/build_multimodal_dataset.py](../functions/tools--build_multimodal_dataset--py.md)
- [tools/build_qwen_four_modal_stress_set.py](../functions/tools--build_qwen_four_modal_stress_set--py.md)
- [tools/build_submission_package.py](../functions/tools--build_submission_package--py.md)
- [tools/calibrate_whisper_confidence.py](../functions/tools--calibrate_whisper_confidence--py.md)
- [tools/capture_qwen_test_image.py](../functions/tools--capture_qwen_test_image--py.md)
- [tools/check_sensor_stability.py](../functions/tools--check_sensor_stability--py.md)
- [tools/collect_qwen_target_scenes.py](../functions/tools--collect_qwen_target_scenes--py.md)
- [tools/create_qwen_launch_logs.py](../functions/tools--create_qwen_launch_logs--py.md)
- [tools/evaluate_saved_asr_nlu.py](../functions/tools--evaluate_saved_asr_nlu--py.md)
- [tools/evaluate_voice_audio.py](../functions/tools--evaluate_voice_audio--py.md)
- [tools/export_group1_sensevoice_onnx_static.py](../functions/tools--export_group1_sensevoice_onnx_static--py.md)
- [tools/finalize_four_modal_report.py](../functions/tools--finalize_four_modal_report--py.md)
- [tools/four_modal_metrics.py](../functions/tools--four_modal_metrics--py.md)
- [tools/frozen_text_hash.py](../functions/tools--frozen_text_hash--py.md)
- [tools/generate_model_manifest.py](../functions/tools--generate_model_manifest--py.md)
- [tools/generate_source_manifest.py](../functions/tools--generate_source_manifest--py.md)
- [tools/generate_wheelhouse_lock.py](../functions/tools--generate_wheelhouse_lock--py.md)
- [tools/live_carla_viewer.py](../functions/tools--live_carla_viewer--py.md)
- [tools/prepare_group1_voice_dataset.py](../functions/tools--prepare_group1_voice_dataset--py.md)
- [tools/probe_s2_route_anchor.py](../functions/tools--probe_s2_route_anchor--py.md)
- [tools/promote_reference_run.py](../functions/tools--promote_reference_run--py.md)
- [tools/qwen_remote_smoke.py](../functions/tools--qwen_remote_smoke--py.md)
- [tools/replay_acceptance.py](../functions/tools--replay_acceptance--py.md)
- [tools/repro_cli.py](../functions/tools--repro_cli--py.md)
- [tools/run_acceptance_suite_a800.py](../functions/tools--run_acceptance_suite_a800--py.md)
- [tools/run_carla_scenario_matrix.py](../functions/tools--run_carla_scenario_matrix--py.md)
- [tools/run_control_safety_benchmark.py](../functions/tools--run_control_safety_benchmark--py.md)
- [tools/run_four_modal_full_chain.py](../functions/tools--run_four_modal_full_chain--py.md)
- [tools/run_generalization_gate.py](../functions/tools--run_generalization_gate--py.md)
- [tools/run_group1_voice_onnx_benchmark.py](../functions/tools--run_group1_voice_onnx_benchmark--py.md)
- [tools/run_group1_voice_text_regression.py](../functions/tools--run_group1_voice_text_regression--py.md)
- [tools/run_long_stability.py](../functions/tools--run_long_stability--py.md)
- [tools/run_qwen3vl_2b_vllm_cu132.sh](../functions/tools--run_qwen3vl_2b_vllm_cu132--sh.md)
- [tools/run_qwen_batch_benchmark.py](../functions/tools--run_qwen_batch_benchmark--py.md)
- [tools/run_qwen_carla_closed_loop.py](../functions/tools--run_qwen_carla_closed_loop--py.md)
- [tools/run_qwen_expanded_instruction_benchmark.py](../functions/tools--run_qwen_expanded_instruction_benchmark--py.md)
- [tools/run_qwen_latency_gate.py](../functions/tools--run_qwen_latency_gate--py.md)
- [tools/run_qwen_vl_decision.py](../functions/tools--run_qwen_vl_decision--py.md)
- [tools/synthesize_stress_audio.py](../functions/tools--synthesize_stress_audio--py.md)
- [tools/validate_c_role.py](../functions/tools--validate_c_role--py.md)
- [tools/validate_control_generalization.py](../functions/tools--validate_control_generalization--py.md)
- [tools/validate_four_modal_dataset.py](../functions/tools--validate_four_modal_dataset--py.md)
- [tools/validate_language_testset.py](../functions/tools--validate_language_testset--py.md)
- [tools/validate_multimodal_dataset.py](../functions/tools--validate_multimodal_dataset--py.md)
- [tools/validate_official_scenes.py](../functions/tools--validate_official_scenes--py.md)
- [tools/validate_route_generalization.py](../functions/tools--validate_route_generalization--py.md)
- [tools/validate_s2_member3_evidence.py](../functions/tools--validate_s2_member3_evidence--py.md)
- [tools/validate_s3_member4_evidence.py](../functions/tools--validate_s3_member4_evidence--py.md)
- [tools/validate_scenarios.py](../functions/tools--validate_scenarios--py.md)
- [tools/verify_model_manifest.py](../functions/tools--verify_model_manifest--py.md)
- [tools/verify_qwen_kernel.py](../functions/tools--verify_qwen_kernel--py.md)
- [tools/verify_release_lock.py](../functions/tools--verify_release_lock--py.md)
- [tools/verify_vllm_cu132_inputs.py](../functions/tools--verify_vllm_cu132_inputs--py.md)
- [tools/verify_voice_weights.py](../functions/tools--verify_voice_weights--py.md)
- [tools/verify_wheelhouse_lock.py](../functions/tools--verify_wheelhouse_lock--py.md)

## 诊断与维护交接

本模块证据：参数、cwd、返回码、原始输出；工具成功不等于业务验收。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

## 第20模块逐入口精读结论（2026-09-22）

本轮按基线 `4e41f990` 核对63份Python工具页、6份运行脚本页和共享环境语义页，改写342处泛用占位。至此20个模块的原泛用入口占位已清零；这只代表入口说明已经落到具体职责，不代表这些可能写文件、启动服务或连接CARLA的工具都被执行。

### 工具分层与副作用

- `validate_*`、`verify_*`、`benchmark_audit` 读取合同、manifest或证据并以返回码/报告表达局部门禁；它们检查什么由函数体决定，不能把一个validator的PASS扩大成全项目PASS。
- `build_*`、`generate_*`、`prepare_*`、`collect_*` 会生成或改写数据、清单、场景或提交材料；执行前固定输入和目标目录，执行后重算hash并由消费方验证。
- `run_*`、`live_carla_viewer`、远端Qwen/CARLA工具会启动服务、连接外部进程、生成actor或写运行产物；只在目标环境中按runbook执行，文档核对不代替实跑。
- 校准、音频合成、模型导出和kernel/wheelhouse工具依赖额外模型、GPU、音频库或构建环境；缺依赖必须报环境门禁，不能默认为代码失败或静默跳过。

### 参数、路径与证据边界

每个Python CLI的argparse默认、类型、choices和布尔action已保留在逐文件页；Shell/PowerShell转发参数另按脚本读取。相对路径通常受cwd影响，输出目录可能已有历史文件，所以可复现命令必须记录cwd、源码SHA、完整参数、输入manifest、退出码和新生成文件hash。报告生成器只聚合其输入，不会自动证明输入来自同一版本或真实生产backend。

### 维护门禁

修改工具时先确定它属于只读校验、派生产物还是外部执行，再回归正常输入、缺文件、坏Schema、重复/泄漏、非零退出和覆盖行为。生成器与validator应成对验证；评分/报告工具还需用已知golden输入核对数值和失败传播。A09测试发现范围和可选声学依赖、A06旧脚本cwd问题继续保留，不能通过减少测试收集或忽略失败来获得“全绿”。

完成本模块后，后续文档工作应转为关闭AUDIT中的实际代码/证据问题和按环境执行门禁，而不是继续新增同义占位说明。
