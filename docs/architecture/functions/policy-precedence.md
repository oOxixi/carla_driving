# 感知与安全配置如何生效

上级：[配置与场景模块](../modules/support-config-scenarios.md)。

## 不存在一个覆盖所有参数的全局优先级

本仓库同时有 `DEFAULT_STRATEGY`、DrivingPolicy、CLI 参数、场景 extensions 和 OrchestratorConfig。维护时必须跟踪具体字段在哪个构造调用中传入；不能仅根据配置文件名称判断哪份最终生效。

## 已核实的装载关系

- [config.strategy](../../../config/strategy.py) 严格读取 strategy_config.yaml。文件虽叫 YAML，内容采用 JSON 语法，可由标准库 json 解析。C/D 若只用默认参数，会继承 DEFAULT_STRATEGY 的相应值。
- [load_driving_policy](../../../integration/driving_policy.py) 默认读 config/driving_policy.json，要求 schema_version=1.0、perception/safety 为对象，并在返回前实际构造两组参数校验数值。
- `perception_parameters(visual_confidence_override=...)`：显式 override 非 None 时替换文件中的 visual_confidence_threshold；否则用文件值。
- `safety_config(route_deviation_override_m=..., stop_line_guard_override_m=...)`：显式覆盖相应字段；maximum_lane_offset 取配置值与最终 route_deviation 的较小者，若干 minimum 值又受 DEFAULT_STRATEGY 限制。因此改一个上限会影响多个衍生值。
- runner 加载场景合同后可覆盖 map/fixed delta/frames/scenario id；实际 control_policy/CLI 注入位置必须查 runner 和 scenario_extensions。
- OrchestratorConfig 仍有独立默认值，不自动读取所有 C/D 策略。

## 为什么保留两份配置

strategy 是跨控制模块的基础默认；DrivingPolicy 构造感知和 Supervisor 的一组具体运行参数，含校验和派生。两者有关联但不等价。后续是否统一物理存储，应先列出每字段生产者/消费者，不能简单删除其中之一。

## 改安全阈值的核对步骤

先确认当前入口是否显式传参，再看构造后值，接着核对 C 的限速/风险和 D 的仲裁是否都使用预期值，最后查日志/manifest 是否记录实际配置。要分别覆盖无 override、有 override、非法值和派生 min/max 约束。

验证入口：[test_driving_policy.py](../../../integration/tests/test_driving_policy.py)、[C tests](../../../car_control_C/tests)、[D tests](../../../car_control_D/tests)。修改运行数值不是只更新 JSON 的文档工作，本轮没有修改这些值。
