# 第二组共享接口 V1

本目录由角色 A 维护，是 A/B/C/D 之间唯一允许的结构化交接契约。当前冻结版本为
`1.0`，所有时间戳均使用单调时钟纳秒或 CARLA 仿真秒，所有距离使用米、速度使用
米每秒、加速度使用米每二次方秒、角度使用度。

## 七类接口

| 文件 | 交接方向 | 用途 |
|---|---|---|
| `driving_command.schema.json` | ASR/NLU → A | 原始驾驶意图与有效期 |
| `model_request.schema.json` | A → B | 异步复杂决策请求 |
| `decision_plan.schema.json` | B → A | 仅高层决策，禁止底层控制量 |
| `maneuver_plan.schema.json` | B → A | Planner V2 的 1–4 步受限复杂机动计划 |
| `perception_state.schema.json` | C → A/B/D | 同帧融合状态与模态有效性 |
| `control_command.schema.json` | A → D | 已校验快/慢路径命令 |
| `execution_feedback.schema.json` | D → A | 命令生命周期、终态与安全事件 |

每个 Schema 内置 `examples`。正例同时单独保存在 `examples/`，便于服务、测试和
回放脚本直接读取。

## 版本规则

1. V1 接口的 `schema_version` 必须精确等于 `1.0`；ManeuverPlan 使用独立的
   `2.0`，禁止隐式兼容未知版本。
2. V1 内只允许增加有默认语义的可选字段；删除、改名、改单位、扩大枚举均需要
   新主版本并同时更新全部生产者和消费者。
3. 所有对象默认 `additionalProperties: false`。未知字段必须在 A 边界被拒绝，不能
   被静默丢弃。
4. `deadline_ns`/`valid_until_ns` 是包含边界：当前单调时钟达到该值时即视为过期。
5. B 的 `DecisionPlan` 不得包含 `throttle`、`brake`、`steer` 或其他底层执行值；
   最终 CARLA `VehicleControl` 只能由 D 产生。
6. 生产证据必须记录 Schema 文件 SHA-256；接口变更后旧结果不得冒充新版本结果。

验证命令：

```bash
python -m pytest -q integration/tests/test_interface_schemas.py
```
