# Day22 第一组交接说明

## 已完成
- smoke/safety 场景验证；
- 红灯、前车、行人、低置信度、TTC、传感器缺失覆盖；
- 防止无目标幻觉；
- 禁止底层控制量；
- 高层动作接口冻结；
- 批量结果与验证报告生成。

## 接口
输入：`voice_command + perception + safety_state`

输出：
- `action`
- `confidence`
- `requires_confirmation`
- `reason_zh`
- `target_speed_mps`（可选）

低置信度统一：
```text
action=STOP
requires_confirmation=true
```

不新增 `STOP_CONFIRM`，避免第二组增加未冻结动作分支。

## 控制链
```text
用户命令/RGB语义/第二组SafetyState
  -> Day22QwenAdapter
  -> 高层Decision
  -> command_adapter
  -> A运行时
  -> B/C控制
  -> D最终安全仲裁
  -> CARLA
```

第一组不调用 `vehicle.apply_control()`。

## 回归
```bash
python -m integration.day22.day22_smoke_test
python -m integration.day22.day22_safety_test
python -m integration.day22.generate_day22_results
python -m integration.day22.generate_day22_validation_report
```
