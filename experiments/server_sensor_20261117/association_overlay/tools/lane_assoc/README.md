# 目标与车道关联：三车固定帧实验

本工作位于独立工作树和实验 CARLA 实例，未修改原生产工作区，未接入驾驶控制或冻结接口。基准提交为 69db71a8；新增代码目前未提交。

- 先使用已有 YOLO 检测、跟踪和实验性 RGB/LiDAR/Radar 融合；
- integration/target_lane_association.py 将传感器位置映射到沿自车道路的中心线，输出 CURRENT / LEFT / RIGHT、AHEAD / BEHIND / UNKNOWN 及沿路距离。分叉、路口、车道边界及不可匹配情况保守输出 UNKNOWN；
- build_follow_candidates 仅保留当前车道前方、有有限非负距离的车辆。该结果目前仅为实验，不代表安全放行；
- run_three_car.py 在单独的 Town05 模拟器上生成同车道前、左前、右前三辆静止车辆，采集同步帧；场景角色仅用于事后 IoU 核查；
- run_models.py 只在感知检查通过后，把唯一候选交给学生和教师进行离线推理，不调用车辆控制；
- make_diagram.py 把识别结果绘制成示意图，非仿真俯视画面。

运行记录和原始传感器数据在 /home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/lane_assoc_20261117/。run.log 是首轮同步失败日志，run5.log 是最终代码的测试记录。项目现有目标证据逻辑的检测置信度阈值为 0.8；本次同车道目标置信度低于该阈值，没有运行完整安全链，不能把模型输出当作车辆执行许可。

检查：pytest -q integration/tests/test_target_lane_association.py。覆盖弯道相对距离、左/右、后方、车道边界、路口、分叉以及候选过滤；这些是代码级验证，不是完整驾驶场景验收。

学生是尚待独立验收的 A3 robust v3 FP32 候选，教师为 Qwen/Qwen3.5-2B。学生只有一个候选，模型输出正确不代表多目标能力已经通过。传感器融合为 FUSED_UNVALIDATED，不代表已经完成定位精度或安全验证。
