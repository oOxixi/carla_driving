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

## 第9模块逐入口精读结论（2026-09-22）

### 权威边界与验证层次

1. `interfaces/*.schema.json` 是七种跨模块 JSON 对象的结构权威；进程内 dataclass、示例 JSON 和 Adapter 均不能代替 Schema。
2. [InterfaceRegistry](../../../runtime/interface_registry.py) 先按对应 Schema 校验，再以 `allow_nan=False` 做 JSON 往返；返回值是与调用方嵌套对象脱离的 `dict`。它只证明结构、枚举、范围和 JSON 可序列化性，不证明目标仍存在、坐标来源正确或动作可执行。
3. [canonical_bridge](../../../integration/canonical_bridge.py) 是旧 CARLA 循环与冻结对象之间的表示转换，不是另一个业务规划器。其默认值、单位换算和字段降级会改变语义，必须在接口证据中记录转换前后对象。
4. `PlanValidator`、`PlanCompiler`、安全仲裁和评分分别追加可执行性、内部步骤、安全和任务通过条件；任一后层 PASS 都不能倒推原始数据来源正确。

### 三个转换入口的实际语义

| 入口 | 关键转换 | 默认/降级 | 不能据此证明 |
|---|---|---|---|
| `voice_envelope_to_driving_command` | intent 归一化；左右后缀转 `direction`；`target_actor_id` 转 `target_id`；km/h 除以 3.6 | 非法 TTL 回退 3 s；非法 confidence 回退 0 并夹到 `[0,1]`；未知速度单位当前按 m/s 原值使用 | 未知单位已被拒绝、语音内容真实、命令可执行 |
| `perception_frame_to_state` | RGB 框中心估 lateral；类别归一化；canonical 坐标采用前 x/左 y/上 z | 缺距离补 50 m；缺 track ID 生成 legacy 类别索引；只有列表首项取 `lead_speed_mps`，其余速度补 0 | 多目标速度关联正确、传感器真的有效、目标 ID 跨帧稳定 |
| `control_command_to_voice_envelope` | 高层 behavior 映旧 runtime intent；复杂动作只允许已编译 `QWEN_DECISION_PLAN` | TTL 至少 0.1 s；FOLLOW 无速度时退 KEEP_LANE；目标 ID 不进入旧低层目标槽位 | 上游过期检查已完成、复杂动作已经被低层执行 |

### 单位、坐标、ID 与时钟维护规则

- 速度进入 canonical 合同后统一为 m/s；角度/转向仍需按具体 B 控制接口核对弧度和归一化 steering，不能靠字段名猜单位。
- `perception_state.coordinate_frame` 固定 `ego_front_x_left_y_up_z_m`；CARLA 原生右手/右向 y 的翻转只能在明确 adapter 边界完成一次。
- `request_id`、`command_id`、`plan_id`、`step_id` 与目标 `target_id` 各自承担不同关联关系；Student pointer 必须按同一请求的候选顺序还原，不能把动态 ID 训练成类别。
- `received_at_ns`、`created_at_ns`、`deadline_ns`、`valid_until_ns` 是纳秒时间边界；`sim_time_s` 是仿真秒。到达截止时刻即过期，不得把 wall/monotonic/CARLA 时钟直接相减。

### 当前边界与联动修改

- M09-01：legacy voice envelope 的未知速度单位未被拒绝，见 [AUDIT](../AUDIT.md)。修复时需同时决定允许单位集合、旧客户端兼容、Schema/Adapter 错误语义及测试，不能只在一端静默换算。
- M06-02 仍适用于本模块：perception 转换按对象列表首项绑定 lead speed。修复目标关联时须同步回归 Qwen 排序、Student target pointer、TTC 和 NONE/缺测。
- 修改 Schema 必须更新 producer、consumer、示例、冻结指纹、Teacher 数据、Student 标签/预处理及版本迁移；只更新 hash 不构成兼容证明。


## Validation entry points

`python -m pytest integration/tests/test_interface_schemas.py integration/tests/test_maneuver_plan_schema.py integration/tests/test_canonical_bridge.py`

Run from the worktree root. 本轮执行结果为 **43 passed in 0.55s**；只覆盖离线 Schema/Adapter 行为，不包含 CARLA、远端模型或硬件验收。

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
