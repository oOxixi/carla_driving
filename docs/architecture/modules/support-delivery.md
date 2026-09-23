# Deployment, datasets and submission evidence

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [运行入口、依赖和产物维护](../functions/environment-delivery.md)

Parent: [Support module](../modules/support.md).

## Deployment functions

[docker/compose.yaml](../../../docker/compose.yaml) defines services/environment. Dockerfile.controller, Dockerfile.qwen-cu132 and Dockerfile.vllm-builder-cu132 build control, inference and builder environments. requirements and lock files are image inputs; patches/vllm-cu132-torch.patch is a build compatibility patch.

[docker/entrypoints/qwen.sh](../../../docker/entrypoints/qwen.sh) fixes qwen3vl-2b-int4 and h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4, verifies model manifest, then observes model list/AutoGPTQ/Marlin logs before recording startup evidence. controller.sh verifies ASR/LoRA before command execution. docker/scripts handles image export and stack checks.

scripts/run_official_scenes.ps1 and run_official_s2_member3.sh/run_official_s3_member4.sh wrap official runs. fetch_scenario_runner.ps1/run_scenario_runner.ps1 manage third-party ScenarioRunner. scripts/run_full_pipeline.sh is the older local Qwen wrapper: line 4 incorrectly resolves project_root to scripts itself, then lines 53/107/166 cd there. Python module lookup and artifact paths therefore depend on unintended external setup; repair or retire before presenting it as verified.

## Dataset and evidence functions

[datasets/README.md](../../../datasets/README.md): language_v1 is text command regression; multimodal_v1 holds schema/card template/examples; qwen_proxy_v1 is action/target proxy regression; repro contains frozen latency inputs/RGB. Large real media/derived sets belong under artifacts or external storage.

[CARLA-Language-Benchmark](../../../CARLA-Language-Benchmark/README.md) owns normalized language data, dataset_card and freeze_p0 checksum/metric_policy. Merge/normalize scripts prepare inputs. tools/benchmark_audit.py is the audit implementation; both hyphenated and underscored directories' audit_global_benchmark_v1.py are compatibility import wrappers, not competing algorithms.

[submission/README.md](../../../submission/README.md) indexes current/technical_solution.md and DEMO_RECORD/EVIDENCE_INDEX templates. build_submission_package, source/model manifests and release locks bind artifacts to identities/hashes. promote_reference_run changes the selected reference and requires valid source evidence. Preserve actual scene, code SHA, model version and file hashes; proxy/development runs do not prove hidden official accuracy.

## Validation and coordinated edits

Verify models/wheelhouse/release locks, then GPU/kernel/service readiness and actual CARLA runs. Missing assets mean unverified, not passed. Data edits affect schema/checksum/card/split/metric policy; model edits affect manifests/image inputs/runtime record; dependency edits affect requirements/locks/Dockerfiles/patches/offline validation. See [complete tool index](support-tools.md).


## 模块接口与参数核对（2026-09-20）

环境交付包含requirements/Docker/weights/datasets/submission和运行脚本；这些是资源与启动协议，不应伪装成单个Python函数接口。模型文件名不证明权重身份，manifest与实际文件hash共同确认。

### 参数语义与生效边界

输入是构建上下文、镜像/依赖版本、挂载路径、环境变量、入口CLI与模型配置；输出是镜像/运行产物/交付材料。具体参数归属各启动脚本，既有逐文件页为完整索引；脚本未实现help时不能假设--help无副作用。

### 上下游与修改影响

修改镜像/依赖需核对安装层与实际启动解释器、cwd、端口、GPU/SDK及权重路径。产物生成命令可能覆盖文件或启动服务，阅读入口与输出目录后再执行；报告不追溯套用新版本。

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [CARLA-Language-Benchmark/tools/audit_global_benchmark_v1.py](../functions/CARLA-Language-Benchmark--tools--audit_global_benchmark_v1--py.md)
- [CARLA-Language-Benchmark/tools/merge_carla_language_benchmark_v1.py](../functions/CARLA-Language-Benchmark--tools--merge_carla_language_benchmark_v1--py.md)
- [CARLA-Language-Benchmark/tools/normalize_carla_benchmark_schema_v1.py](../functions/CARLA-Language-Benchmark--tools--normalize_carla_benchmark_schema_v1--py.md)
- [CARLA_Language_Benchmark/__init__.py](../functions/CARLA_Language_Benchmark--__init__--py.md)
- [CARLA_Language_Benchmark/tools/__init__.py](../functions/CARLA_Language_Benchmark--tools--__init__--py.md)
- [CARLA_Language_Benchmark/tools/audit_global_benchmark_v1.py](../functions/CARLA_Language_Benchmark--tools--audit_global_benchmark_v1--py.md)
- [datasets/multimodal_v1/schema.json](../functions/datasets--multimodal_v1--schema--json.md)
- [docker/Dockerfile.controller](../functions/docker--Dockerfile--controller.md)
- [docker/Dockerfile.qwen-cu132](../functions/docker--Dockerfile--qwen-cu132.md)
- [docker/Dockerfile.vllm-builder-cu132](../functions/docker--Dockerfile--vllm-builder-cu132.md)
- [docker/compose.yaml](../functions/docker--compose--yaml.md)
- [docker/entrypoints/controller.sh](../functions/docker--entrypoints--controller--sh.md)
- [docker/entrypoints/qwen.sh](../functions/docker--entrypoints--qwen--sh.md)
- [docker/requirements-controller.lock.txt](../functions/docker--requirements-controller--lock--txt.md)
- [docker/requirements-controller.txt](../functions/docker--requirements-controller--txt.md)
- [docker/requirements-cu132-build.lock.txt](../functions/docker--requirements-cu132-build--lock--txt.md)
- [docker/requirements-cu132-build.txt](../functions/docker--requirements-cu132-build--txt.md)
- [docker/requirements-qwen.lock.txt](../functions/docker--requirements-qwen--lock--txt.md)
- [docker/requirements-qwen.txt](../functions/docker--requirements-qwen--txt.md)
- [docker/requirements-voice.txt](../functions/docker--requirements-voice--txt.md)
- [docker/scripts/export-images.ps1](../functions/docker--scripts--export-images--ps1.md)
- [docker/scripts/verify-stack.ps1](../functions/docker--scripts--verify-stack--ps1.md)
- [notebooks/reproduce.ipynb](../functions/notebooks--reproduce--ipynb.md)
- [notebooks/voice_to_carla_runbook.ipynb](../functions/notebooks--voice_to_carla_runbook--ipynb.md)
- [pytest.ini](../functions/pytest--ini.md)
- [requirements-qwen-client.txt](../functions/requirements-qwen-client--txt.md)
- [requirements-qwen-vllm.txt](../functions/requirements-qwen-vllm--txt.md)
- [requirements-qwen.txt](../functions/requirements-qwen--txt.md)
- [requirements.txt](../functions/requirements--txt.md)
- [run.ps1](../functions/run--ps1.md)
- [run.sh](../functions/run--sh.md)
- [stop.ps1](../functions/stop--ps1.md)
- [stop.sh](../functions/stop--sh.md)
- [weights/download_asr_fallback.sh](../functions/weights--download_asr_fallback--sh.md)
- [weights/download_fallback.sh](../functions/weights--download_fallback--sh.md)
- [weights/download_optional_models.sh](../functions/weights--download_optional_models--sh.md)

## 诊断与维护交接

本模块证据：镜像依赖、cwd、模型路径/manifest；确认宿主容器映射。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

### 已核对的容器入口参数

| 入口 | 构建/运行声明 | 消费与限制 |
|---|---|---|
| [Dockerfile.controller](../../../docker/Dockerfile.controller) | HF_HUB_OFFLINE=1、TRANSFORMERS_OFFLINE=1；SCENARIO_RUNNER_ROOT=/opt/scenario_runner；PYTHONPATH=/opt/scenario_runner:/app；REPRO_DATA_ROOT=/app/release_data | ENTRYPOINT为/app/docker/entrypoints/controller.sh；默认CMD是python3 -m integration.demo_offline，不能把启动此镜像默认视为真实CARLA闭环 |
| [Dockerfile.qwen-cu132](../../../docker/Dockerfile.qwen-cu132) | 离线模型环境，VLLM_NO_USAGE_STATS=1；EXPOSE 8001 | ENTRYPOINT=/usr/local/bin/qwen-entrypoint；EXPOSE只是镜像声明，主机端口发布和服务地址仍由实际启动决定 |

这些目录是容器内路径，不能直接当宿主路径。修改镜像CMD/ENTRYPOINT后需同步调用脚本和运行说明。shell参数完整性需阅读各脚本，Python argparse统计不覆盖它们。

## 第19模块逐入口精读结论（2026-09-22）

本轮按基线 `4e41f990` 核对37份容器、依赖、脚本、数据与交付页面，改写4处Python入口的泛用占位。资源文件没有函数占位并不表示已完成构建；本模块的核心是把代码、依赖、模型、数据和证据绑定成可复现身份。

### 构建、启动与模型身份

controller、Qwen和vLLM builder是不同镜像合同，requirements输入、CUDA/PyTorch/vLLM组合、离线环境、挂载和ENTRYPOINT均不能交叉推断。controller默认CMD是 `integration.demo_offline`，不是CARLA闭环；Qwen镜像 `EXPOSE 8001` 也不代表宿主已发布该端口或服务可达。生产模型必须同时核对repo/revision、artifact fingerprint、model manifest、容器内路径和运行时返回的model identity。

### 数据与提交证据

datasets、CARLA Language Benchmark、release locks和submission package分别管理样本合同、冻结基准、发布身份与最终材料。原始数据、派生数据、冻结split和报告必须通过hash/manifest连接；复制文件或重写可移植RGB路径后必须重签发布hash，不能沿用源清单声称发布内容未变。reference promotion会改变当前引用，执行前要验证来源证据，执行后要保存旧/新身份和生成日志。

### 运行脚本与已知边界

A06仍未关闭：旧 `scripts/run_full_pipeline.sh` 把 `scripts` 目录算作项目根，模块查找和产物路径依赖偶然外部环境。在修复并从任意cwd验证前，不得把它列为正式一键复现入口。Shell/PowerShell、notebook与Docker入口的参数和cwd各自独立；`--help`、镜像构建成功或文件存在都不等于场景、模型或提交Gate通过。

### 交付门禁

最低顺序是依赖/lock与wheelhouse核验、源码/模型manifest核验、镜像构建、容器内health与独立infer、CARLA场景证据、报告/附件hash，最后生成submission package并在干净环境复核。每级失败保留原始日志和退出码；缺GPU、权重、CARLA或外部runner时明确写未验证，不能用mock或历史报告补齐。
