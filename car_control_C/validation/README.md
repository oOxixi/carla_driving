# C 感知与纵向控制验证

本目录只保存验证方法说明，不保存某次运行生成的 CSV。验证范围包括：

- RGB/LiDAR/Radar 帧号、时间戳和外参审计；
- 前向距离、相对速度、TTC 与风险等级；
- 行人视觉证据以及无可靠测距时的 fail-closed 行为；
- 摄像头黑屏、Radar 掉线、LiDAR 缺帧、误检和延迟注入。

确定性检查：

```bash
python tools/validate_c_role.py
python -m pytest -q car_control_C/tests integration/tests
```

CARLA 传感器验收应使用 `--perception-mode sensors`，并把原始 `.jsonl`、摘要和故障注入
结果写入 `artifacts/`。不得把 `world`/场景真值当成真实感知证据。
