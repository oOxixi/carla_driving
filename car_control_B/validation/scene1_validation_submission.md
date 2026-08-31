# 成员2场景1基础控制验证说明

## 本次验证

- 日期：2026-08-31
- 代码版本：`b7ee7f1`
- CARLA 地图：`Town10HD_Opt`
- 感知模式：`world`
- 场景事实模式：`fuse`
- Qwen：未接入
- 验证定位：基础控制链路和速度/停车行为验证，不是官方 S1 5 km 正式验收

## 结果结论

| 场景 | 结论 | 主要证据 |
| --- | --- | --- |
| S01_set_speed_20 | FAILED | 车辆路线跟踪和碰撞检查通过，但最终速度为 0.000162 m/s，未满足 20 km/h +/- 5 km/h；日志记录 5 次红灯违规和 5 次安全覆盖 |
| S02_slow_down | SUCCEEDED | 速度从 5.361255 m/s 降至 4.166807 m/s；碰撞和路线偏差均为 0；2 条命令均成功结束 |
| S03_stop | SUCCEEDED | 停车延迟 1.350 s；最终速度约为 0；碰撞和路线偏差均为 0；2 条命令均成功结束 |

## 成员2当前完成情况

- 已验证减速指令能够使车辆速度下降。
- 已验证停车指令能够在限定时间内停车并保持低速状态。
- 已验证三次运行均调用了 B/C/D 控制链路，且生成了 JSONL 和 summary 证据。
- S01 定速场景尚未通过，需要进一步检查红灯检测/安全覆盖触发条件，以及冒烟场景结束时的目标速度判定口径。
- B01-B09 横向专项场景仍需作为成员2的转弯、变道和出弯回正证据单独统计。

## 证据路径

- `artifacts/logs/S01_set_speed_20_20260831_133024_900554.jsonl`
- `artifacts/logs/S01_set_speed_20_20260831_133024_900554.summary.json`
- `artifacts/logs/S02_slow_down_20260831_133152_515767.jsonl`
- `artifacts/logs/S02_slow_down_20260831_133152_515767.summary.json`
- `artifacts/logs/S03_stop_20260831_133328_835949.jsonl`
- `artifacts/logs/S03_stop_20260831_133328_835949.summary.json`

## 未解决问题及复现方法

未全部解决。S01 可按以下命令复现：

```powershell
python -m integration.carla_runner `
  --host 127.0.0.1 `
  --port 2000 `
  --timeout-s 120 `
  --scenario-file scenarios\smoke\S01_set_speed_20.json `
  --scenario-facts-mode scenario `
  --perception-mode world `
  --realtime `
  --use-current-map
```

正式官方场景 S1 仍需 Qwen 服务，因此本记录不能替代官方 S1 的最终验收结果。
