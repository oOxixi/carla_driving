# 7 月 21 日第二组向第一组交接

> 文档状态：截至 7 月 22 日回填，记录已完成的高层命令入口、执行反馈和安全覆盖链路。

## 今日交付结论

第二组可以接收第一组给出的结构化高层动作，并将受支持的动作送入车辆控制闭环。Qwen 只决定“做什么”，控制模块和 D 安全仲裁决定“方向盘、油门和刹车怎么给”。

当前可直接闭环执行的动作：

- `STOP`：舒适停车并进入静止保持。
- `EMERGENCY_STOP`：映射为紧急制动。
- `SET_SPEED`：需要给出非负的 `target_speed_mps`。

当前不能写成已直接执行的动作：`KEEP_LANE`、`SLOW_DOWN`、`CHANGE_LANE`、`TURN`、`AVOID_OBSTACLE` 等复杂动作。没有明确规划结果时，这些动作会进入确认或安全停车，不能仅凭 Qwen 文本直接产生底层控制。

## 已确定的 Qwen 输出格式

```json
{
  "schema_version": "1.0",
  "decision_id": "qwen-0721-001",
  "frame": 1200,
  "action": "STOP",
  "target_speed_mps": null,
  "confidence": 0.96,
  "requires_confirmation": false,
  "reason_zh": "前方红灯且距离停止线较近，安全优先停车"
}
```

约束：

- `action` 必须来自双方固定动作集合。
- `SET_SPEED` 必须提供 `target_speed_mps`；其他动作不应夹带底层控制数值。
- 置信度低、场景矛盾或无法判断时，设置 `requires_confirmation=true`，并输出安全原因。
- `reason_zh` 应简洁说明“看到什么、判断什么、建议什么”，不参与底层控制。

## 安全冲突处理结果

| Qwen 高层动作 | 车辆/融合安全状态 | 最终结果 |
|---|---|---|
| 继续或设定较高速度 | 红灯或停止线约束 | D 覆盖不安全动作，停车 |
| 继续或设定较高速度 | 行人/障碍距离过近 | 减速或紧急制动 |
| 继续或设定较高速度 | TTC 不大于紧急阈值 | 紧急制动 |
| `STOP` | 道路安全 | 执行舒适停车并保持 |
| `EMERGENCY_STOP` | 任意状态 | 立即进入紧急制动 |
| 无法判断/低置信度 | 任意状态 | 请求确认并安全减速或停车 |

关键结论：Qwen 的高层动作是请求，不是最终授权；D 的安全结果始终具有更高优先级。

## 给第一组的执行反馈格式

```json
{
  "decision_id": "qwen-0721-001",
  "accepted_action": "STOP",
  "vehicle_state": "APPROACH_STOP",
  "target_speed_mps": 0.0,
  "safety_override": true,
  "safety_reason": "STOP_LINE_GUARD",
  "terminal_status": "SUCCEEDED",
  "detail_zh": "车辆已停车并保持，安全仲裁覆盖了继续行驶请求"
}
```

`terminal_status` 只应使用 `SUCCEEDED/FAILED/REJECTED/EXPIRED/TIMED_OUT`。第一组可用该反馈检查 Qwen 判断与车辆实际动作是否一致。

## 当日验收记录

- `STOP`、`EMERGENCY_STOP`、`SET_SPEED` 已进入车辆控制链路并有测试覆盖。
- 低置信度、歧义和显式确认请求会进入安全确认流程。
- 红灯、低 TTC、控制冲突等危险条件可以覆盖不安全高层动作。
- 执行反馈已统一为命令终态、车辆状态、安全覆盖标记和中文原因。
