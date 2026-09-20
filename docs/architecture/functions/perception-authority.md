# 同帧感知、目标身份与来源审计

上级：[感知模块](../modules/vehicle-perception.md)。

## 为什么不只传一组“检测结果”

控制需要同帧的距离、速度、灯态、路线和目标身份；日志还必须知道这些值来自真实传感器、地图、场景真值还是估算。即使字段名相同，来源不同也影响能否作为正式感知证据。

## 当前模块链

[CarlaPerceptionBridge.acquire](../../../integration/carla_perception.py) 读取指定 CARLA frame，对 RGB/LiDAR 同帧获取负责，事件传感器由 ledger 对帧归档，Radar 有单独可选等待规则。检测器 [OnnxYoloDetector](../../../integration/rgb_detector.py) 处理图像，追踪器 [SensorObjectTracker](../../../integration/object_tracker.py) 维护跨帧 ID；PerceptionFrame 再转成 C 请求、D 状态与 canonical perception。

[audit_control_sources](../../../integration/perception_stage.py) 将来源归为 SENSOR/MAP/ORACLE/SYNTHETIC/DERIVED/UNKNOWN。场景中的 Actor 名称或出生坐标不应被包装成视觉检测结果；场景 ground truth 可以用于触发与评分，但要和控制输入分开记录。

## 目标与单位转换的维护约束

- canonical 的横向 y-left 与 CARLA 的 y-right 是不同坐标约定；相反符号不自动等于 Bug。
- canonical_bridge 当前包含未知距离补 50m、按框中心估横向位置、非首目标速度补零等近似。这些字段不能被后续文档改称直接测量值。
- 改目标排序/ID 关联要同步 Qwen target grounding、Student pointer、跟车对象与 TARGET_PASSED 判断。
- C 的时序距离变化会推断接近速度，切换最近目标可能造成虚假低 TTC；不能简单用相邻两帧最近距离差当同一目标速度。

## 修改一个感知字段需要查哪里

采集/检测生产端 → PerceptionFrame 类型 → canonical/perception bridge → Schema → C/D/模型消费者 → 来源审计与日志 → 相关场景验收。缺失值是否允许 None、是否采取保守估计必须同时记录，不能仅给字段补默认数值避免异常。

验证：[carla perception tests](../../../integration/tests/test_carla_perception.py)、[canonical bridge tests](../../../integration/tests/test_canonical_bridge.py)、[C safety state tests](../../../car_control_C/tests/test_safety_state.py)、[感知测试集合](../../../integration/tests)。真实视觉效果需要真实输入验证，mock 帧对齐只证明接口时序。
