# JSON contracts and process-local objects

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [版本、时间、坐标与适配语义](../functions/interface-versioning.md)

[Vehicle module](../modules/vehicle.md)

## Responsibility, contracts and failure behavior

interfaces/*.schema.json are authoritative inter-module JSON definitions. InterfaceRegistry validates jsonschema then round-trips JSON to reject NaN/non-JSON values. Contracts include driving_command, model_request, decision_plan, maneuver_plan, perception_state, control_command and execution_feedback. Follow each schema version; the directory is not uniformly V1. Perception coordinates are ego_front_x_left_y_up_z_m. Deadlines use nanoseconds. Examples are samples, not field definitions. A/B/D dataclasses and integration.contracts are process-local adapter boundaries.


## 模块接口与参数核对（2026-09-20）

跨进程合同由interfaces/*.schema.json定义；内部dataclass由各adapter桥接。required、nullable、enum、additionalProperties和版本必须同时检查；示例文件不是完整字段定义。

### 参数语义与生效边界

Schema单位/范围见下层Schema字段表；$ref和oneOf/anyOf条件不能只看顶层type。A内部秒、canonical纳秒、B弧度和车辆角度需要显式转换。接口合法不能证明语义来源合法。

### 上下游与修改影响

变更需联动InterfaceRegistry、所有adapter/producer/consumer、示例、冻结指纹、Teacher/Student及测试；不通过只更新hash来掩盖不兼容变化。

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## Complete implementation inventory

- [interfaces/control_command.schema.json](../../../interfaces/control_command.schema.json) - module/resource/documentation
- [interfaces/decision_plan.schema.json](../../../interfaces/decision_plan.schema.json) - module/resource/documentation
- [interfaces/driving_command.schema.json](../../../interfaces/driving_command.schema.json) - module/resource/documentation
- [interfaces/examples/control_command.json](../../../interfaces/examples/control_command.json) - module/resource/documentation
- [interfaces/examples/decision_plan.json](../../../interfaces/examples/decision_plan.json) - module/resource/documentation
- [interfaces/examples/driving_command.json](../../../interfaces/examples/driving_command.json) - module/resource/documentation
- [interfaces/examples/execution_feedback.json](../../../interfaces/examples/execution_feedback.json) - module/resource/documentation
- [interfaces/examples/maneuver_plan.json](../../../interfaces/examples/maneuver_plan.json) - module/resource/documentation
- [interfaces/examples/model_request.json](../../../interfaces/examples/model_request.json) - module/resource/documentation
- [interfaces/examples/perception_state.json](../../../interfaces/examples/perception_state.json) - module/resource/documentation
- [interfaces/execution_feedback.schema.json](../../../interfaces/execution_feedback.schema.json) - module/resource/documentation
- [interfaces/maneuver_plan.schema.json](../../../interfaces/maneuver_plan.schema.json) - module/resource/documentation
- [interfaces/model_request.schema.json](../../../interfaces/model_request.schema.json) - module/resource/documentation
- [interfaces/perception_state.schema.json](../../../interfaces/perception_state.schema.json) - module/resource/documentation
- [interfaces/README.md](../../../interfaces/README.md) - module/resource/documentation

## Dependencies and coordinated changes


## Validation entry points

`python -m pytest integration/tests/test_interface_schemas.py integration/tests/test_maneuver_plan_schema.py integration/tests/test_canonical_bridge.py`

Run from the worktree root. Listed commands are relevant checks, not claims that tests were executed. CARLA, remote-model and hardware acceptance require their actual environments and run manifests.

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [interfaces/control_command.schema.json](../functions/interfaces--control_command--schema--json.md)
- [interfaces/decision_plan.schema.json](../functions/interfaces--decision_plan--schema--json.md)
- [interfaces/driving_command.schema.json](../functions/interfaces--driving_command--schema--json.md)
- [interfaces/execution_feedback.schema.json](../functions/interfaces--execution_feedback--schema--json.md)
- [interfaces/maneuver_plan.schema.json](../functions/interfaces--maneuver_plan--schema--json.md)
- [interfaces/model_request.schema.json](../functions/interfaces--model_request--schema--json.md)
- [interfaces/perception_state.schema.json](../functions/interfaces--perception_state--schema--json.md)

## 诊断与维护交接

本模块证据：原始JSON、schema版本、单位/坐标转换；合法JSON不等于语义正确。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

### Registry实际入口与Schema索引

实现为[runtime/interface_registry.py](../../../runtime/interface_registry.py)，不是interfaces目录内的registry。`InterfaceRegistry(root=None)`默认定位仓库interfaces；`validate(name,payload)`返回脱离调用方引用的严格JSON dict，拒绝未知接口、非Mapping、Schema错误以及NaN/非JSON对象。`warm(names=None)`预编译并缓存validator。

| 接口 | 版本约束 | 顶层必填字段 | 完整约束 |
|---|---|---|---|
| control_command.schema | `{"const": "1.0"}` | `schema_version`, `command_id`, `path_type`, `behavior`, `target`, `limits`, `issued_at_ns`, `deadline_ns`, `source` | [字段表](../functions/interfaces--control_command--schema--json.md) |
| decision_plan.schema | `{"const": "1.0"}` | `schema_version`, `request_id`, `command_id`, `intent`, `behavior`, `parameters`, `confidence`, `reason_code`, `created_at_ns`, `valid_until_ns` | [字段表](../functions/interfaces--decision_plan--schema--json.md) |
| driving_command.schema | `{"const": "1.0"}` | `schema_version`, `command_id`, `source_text`, `intent`, `parameters`, `confidence`, `received_at_ns`, `deadline_ns`, `source` | [字段表](../functions/interfaces--driving_command--schema--json.md) |
| execution_feedback.schema | `{"const": "1.0"}` | `schema_version`, `command_id`, `status`, `action_summary`, `emitted_at_ns`, `t_action_apply_ns`, `latency_ms`, `safety_event`, `terminal_reason` | [字段表](../functions/interfaces--execution_feedback--schema--json.md) |
| maneuver_plan.schema | `{"const": "2.0"}` | `schema_version`, `request_id`, `command_id`, `plan_id`, `plan_type`, `steps`, `replan_conditions`, `confidence`, `requires_confirmation`, `created_at_ns`, `valid_until_ns`, `reason_code`, `model_id` | [字段表](../functions/interfaces--maneuver_plan--schema--json.md) |
| model_request.schema | `{"const": "1.0"}` | `schema_version`, `request_id`, `command_id`, `created_at_ns`, `deadline_ns`, `source_text`, `scene_summary`, `targets`, `constraints` | [字段表](../functions/interfaces--model_request--schema--json.md) |
| perception_state.schema | `{"const": "1.0"}` | `schema_version`, `frame_id`, `sim_time_s`, `captured_at_ns`, `coordinate_frame`, `objects`, `traffic_light`, `ttc_s`, `min_gap_m`, `risk_level`, `modality_valid`, `stale`, `sync` | [字段表](../functions/interfaces--perception_state--schema--json.md) |
