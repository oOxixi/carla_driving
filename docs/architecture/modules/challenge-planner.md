# Planner 适配、验证与就绪

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [Head解码、约束修复和就绪判定](../functions/student-plan-decoding.md)

上级：[挑战赛道](../modules/challenge.md)。

## 功能与实现

[backend.py](../../../challenge/planner/backend.py) 提供 PlannerBackend 边界；[teacher_backend.py](../../../challenge/planner/teacher_backend.py) 接入 Teacher；[student_backend.py](../../../challenge/planner/student_backend.py) 加载 Student、权重并执行 infer；[student_adapter.py](../../../challenge/planner/student_adapter.py) 将 Head 解码为计划，限制允许行为、速度、完成条件和目标引用；[common.py](../../../challenge/planner/common.py) 构造验证场景；[frozen_contracts.py](../../../challenge/planner/frozen_contracts.py) 检查外部 Schema 指纹。

StudentBackend.infer：InterfaceRegistry.validate(model_request) → StudentPreprocessor → inference_mode 下模型前向 → StudentPlanAdapter.decode → PlanValidator.validate。输入 request_id、command_id 与输出一致，now_ns 取 created_at_ns，允许 confirmation。输出 ManeuverPlan V2，禁止直接输出车辆控制量。

## 权重与 Gate

纯 state_dict 通过 torch.load(weights_only=True) 加载。无权重或无通过 Gate 的 manifest 时 production_ready=False，health 返回失败；这与 infer 可运行结构 smoke 是不同状态。

manifest 必须为 JSON 对象，git_sha/model_id/weights_sha256/dataset_version/config_id/gate_status 均非空字符串，git_sha 为完整 40 位十六进制，model_id/config_id 匹配模型，SHA256 匹配实际权重，gate_status 为 A3_FP32_GATE_PASSED。未知结构或配置不能靠改文档绕过加载验证。

## 测试与联动

[A1 测试](../../../challenge/tests/test_a1_student.py)、[交付测试](../../../challenge/tests/test_delivery.py)。本轮服务器执行结果 **26 passed in 19.76s**。修改 Adapter 时检查 A3 评测是否测原始 Head 还是最终计划，并检查 HIL 实际 infer 一致性；修改健康状态时检查主系统启动和故障降级路径。

风险：加载器验证 manifest 声明及文件身份，不独立重算 Gate。A3 晋级证据的绑定必须由上游补齐，见[训练页](challenge-training.md)。

## 第11模块逐入口精读结论（2026-09-22）

### Teacher/Student 共用边界

- 两个 Backend 都先验证 ModelRequest V1，后验证 ManeuverPlan V2，并在构造时核对两份 Schema 规范化指纹；它们不会修改 A/B/C/D 低层控制链。
- `validation_scene` 只投影请求内摘要、约束、目标和能力，不回读实时 CARLA。若推理期间场景变化，时效和重规划由外层生命周期处理。
- `allow_confirmation=True` 表示 Validator 接受需确认计划返回，不表示确认已获得；编排器必须区分“合法计划”和“可立即执行”。

### Student 解码和确定性修复

| Head/输入 | Adapter最终语义 |
|---|---|
| plan length | argmax+1，夹到模型步数；must_stop强制1步 |
| behavior | 只从请求允许且场景能力可行的行为中按logit选择；空集合回退HOLD并强制确认 |
| pointer | FOLLOW/AVOID只在请求前8个有效目标中选；其他行为不要求目标 |
| lane/completion | 换道/转弯/回原道和多数completion由行为确定性覆盖 |
| speed | 夹到0、代码50、请求speed limit和max target speed的最小值 |
| confirmation | 无可行动作、logit≥0或confidence<0.8任一触发 |
| sequence | STOP/HOLD/PULL_OVER后截断；replan只保留非负logit前8类 |

因此评测必须同时保存原始 Head、修复原因和最终 Plan；只评最终 plan 会掩盖模型输出错误，只评 Head 又不能代表闭环安全结果。

### 就绪、身份和当前边界

- Student 无权重、无manifest或只加载裸state_dict时均可 `infer` 做结构 smoke，但 `health=False`；正式切换必须要求 health 和外部已签发 Gate 证据。
- manifest 绑定 git/model/config/dataset/gate字符串与实际权重SHA，但代码不验证 dataset manifest、Gate报告或签发者；这部分由A3/B2交付链补齐。
- Teacher wrapper 的 production_ready 是构造时快照，正式服务重载后应重建 wrapper 或由上层明确刷新，不能假定字段自动联动。
- M11-01：PULL_OVER 的 predicted lane 不是 SHOULDER 时 Adapter 输出 null lane，而 PlanValidator 当前仍接受；见 [AUDIT](../AUDIT.md)。修复应同时约束 Adapter/Validator/Compiler/闭环控制和训练标签。



## 模块接口与参数核对（2026-09-20）

StudentBackend.infer(request)执行请求校验、预处理、模型推理、adapter解码和PlanValidator，返回ManeuverPlan。PlannerBackend是替换Teacher/Student的边界，返回对象不能直接当车辆低层控制。

### 参数语义与生效边界

StudentBackend的weights/weights_manifest默认None用于结构能力，不意味着production_ready。权重manifest需绑定model/config、SHA和A3_FP32_GATE_PASSED；调用infer与健康就绪是不同条件。target pointer必须对应预处理保留的候选顺序。

### 上下游与修改影响

adapter约束修复会使head预测与最终Plan不同，评估需说明比较层次。修改解码需查训练标签、mask、Validator/Compiler、HIL实际infer一致性和模型身份。

### [challenge/planner/student_backend.py](../../../challenge/planner/student_backend.py) 的入口与声明

```python
StudentBackend.__init__(self, model: StudentPlannerV0 | None=None, *, weights: str | Path | None=None, weights_manifest: str | Path | None=None, registry: InterfaceRegistry | None=None) -> None
StudentBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
StudentBackend.health(self) -> tuple[bool, str]
validate_weight_manifest(weights: str | Path, manifest_path: str | Path, *, expected_model_id: str, expected_config_id: str=StudentModelConfig().config_id) -> dict[str, Any]
```

### [challenge/planner/student_adapter.py](../../../challenge/planner/student_adapter.py) 的入口与声明

```python
StudentPlanAdapter.__init__(self, *, model_id: str='student-v0-r3-fp32') -> None
StudentPlanAdapter.decode(self, request: Mapping[str, Any], outputs: Mapping[str, Tensor]) -> dict[str, Any]
```

### [challenge/planner/backend.py](../../../challenge/planner/backend.py) 的入口与声明

```python
PlannerBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
PlannerBackend.health(self) -> tuple[bool, str]
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `PlannerBackend.model_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `PlannerBackend.production_ready` | `bool` | `无声明默认（构造/赋值方提供）` |

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [challenge/planner/__init__.py](../functions/challenge--planner--__init__--py.md)
- [challenge/planner/backend.py](../functions/challenge--planner--backend--py.md)
- [challenge/planner/common.py](../functions/challenge--planner--common--py.md)
- [challenge/planner/frozen_contracts.py](../functions/challenge--planner--frozen_contracts--py.md)
- [challenge/planner/student_adapter.py](../functions/challenge--planner--student_adapter--py.md)
- [challenge/planner/student_backend.py](../functions/challenge--planner--student_backend--py.md)
- [challenge/planner/teacher_backend.py](../functions/challenge--planner--teacher_backend--py.md)

## 诊断与维护交接

本模块证据：head、pointer/NONE、修复原因、权重身份；需对应真实输入。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。
