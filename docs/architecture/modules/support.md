# Support modules

本页为可选分组索引。正常开发按 [项目入口](../README.md) 直接进入具体业务模块，再进入功能文档，共三级。

Scope: voice_group, qwen_service, config, scenarios, docker, scripts, tools, submission, datasets, CARLA-Language-Benchmark and CARLA_Language_Benchmark. These modules connect input, services, environment and evidence to the driving pipeline.

| Function page | Responsibility |
|---|---|
| [Voice](../modules/support-voice.md) | ASR, verification, intent/slots, weights and audio evidence |
| [Qwen](../modules/support-qwen.md) | HTTP/backend behavior, production readiness and historical protocol |
| [Configuration/scenarios](../modules/support-config-scenarios.md) | Policy ownership, overrides, scenario layers and validation |
| [Deployment/delivery](../modules/support-delivery.md) | Docker, launchers, datasets and evidence packaging |
| [Complete tools](../modules/support-tools.md) | Every support script grouped by function |

Review interfaces and effective configuration ownership before cross-module changes; follow each page's dependency checklist. Confirmed findings: stale server tests fail collection, vLLM health does not probe its backend, and the older full-pipeline launcher resolves the wrong project root. Documentation does not establish new GPU/model/CARLA acceptance evidence.
