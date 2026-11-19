# 单帧检测框分组与点云归属：隔离验收

本工作在独立工作树进行，未接入既有驾驶控制。`integration/duplicate_detection_grouper.py` 和 `integration/target_group_localization.py` 不读取 CARLA Actor、语义 LiDAR 真值或场景角色；这些只用于回放后评分。未训练或替换检测模型。

## 模块接口

`localize_groups(objects, lidar, rgb, radar, ego_transform, camera_fov=100, history=None)` 返回 groups、原始点的 `point_state` / `point_owner` / `point_reason` 及诊断几何。每个组保存所有成员框、原始类别和置信度，不把 car/truck 差异当作物理身份差异。不同稳定轨迹可阻止合组；本次无轨迹记录，未提供历史数据。

分组须满足 IoU >=0.90、中心及尺寸一致、独立选中簇至少 5 点、选中点交并比 >=0.8、前向中心差 <0.5m，且没有足够明显的其他深度簇或距离选中簇 4.5–15m 的未选中非地面候选点。最后这条是根据 16 组人工压力样本收紧的探索性门槛，并非充分验证的通用规则；它可能把背景点误当作需要保留的竞争假设。证据不足时不合组。不同组重叠点采用归一化中心距离及三维簇距离一致的严格筛选，否则保留 AMBIGUOUS。

点状态编码 0=AMBIGUOUS、1=ASSIGNED、2=ENVIRONMENT，所有非 ASSIGNED 点 owner 为 -1。当前没有独立可靠的环境分类证据，接近地面平面的点仍保留 AMBIGUOUS，ENVIRONMENT 本次不会被自动断言。reason 0=框外、1=重叠未定、2=近地面、3=候选但未入选、4=选中、5=高度过滤、6=地面平面不可用。原始传感器文件始终保留，所有筛选的状态和原因均保留。点簇质量包含前后/左右/高度范围、距离 IQR/标准差、二维框内部一致性、警示；不声明可恢复车辆中心或占据范围。

## 数据和指标

- 旧回放 55 帧在 `pointcloud_group_regression55_20261117`：121/170 → 122/170；已评分 3722/3722 归属正确；匹配框内目标点召回 3722/4951。旧回放没有保存时间戳，使用同一帧 ID、相同占位时间戳重放；不能把它当作时间同步实测。
- 新采集 `pointcloud_overlap20_raw_20261117` 共 20 帧；另有 sweep 10、focus 12、holdout 12。首批 5 帧基于真实 YOLO 框人为注入跨类别重复框，不是自然检测结果。所有新场景保留原始图像、LiDAR、语义 LiDAR、Radar、帧号和各传感器时间戳。
- 54 新帧中真值车辆投影重叠 33 帧，两辆车均匹配检测 20 帧，原始 YOLO 检测框重叠 19 帧；未匹配的不计入误合并分母。标定的真值包围盒使用 IoU 进行近似匹配，遮挡和紧邻条件下仍可能误匹配。
- 人为严重重叠压力测试：`pointcloud_group_adversarial_20261117` 是通过放宽不同真实车辆的原始检测框构造；调整前 3/16 误合并，针对这批加深度保守规则后 0/16。后采集 `pointcloud_group_holdout_adversarial_20261117` 为 0/8，仍只是小样本。
- Precision 只计与目标及语义点可匹配的已分配点；同时报告未评分数。Recall 只计匹配检测框内、语义真值可识别的目标 LiDAR 点，漏检车辆不在分母内。定位覆盖率包括预期车辆，无匹配框也算失败。CARLA 语义 LiDAR 最近邻 <=0.08m 仅为离线参考，可能存在近邻误匹配；不是实车真值。
- 测距是自车原点与车辆包围盒最近水平表面之差；旧失败目标未存距离真值，不计入误差，无法检验 T1 的真实测距误差。原先已成功的 184 个可成对比较样本最大差 0.017m，P95 差 0.000002m。
- 109 帧、1264849 点做过状态/owner/原因完整性核验；每个 ASSIGNED 点唯一 owner。未证明全天候、动态场景或实车安全。

运行测试：
`PYTHONPATH=$PWD /home/tiaozhansai/carla-driving-challenge/.venv/bin/python -m pytest -q integration/tests/test_duplicate_detection_grouper.py integration/tests/test_target_pointcloud_localization.py integration/tests/test_pointcloud_p0_audit.py integration/tests/test_target_lane_association.py`

旧数据回放：`PYTHONPATH=$PWD /home/tiaozhansai/carla-driving-challenge/.venv/bin/python tools/pointcloud_p0/regress_groups.py`

网页数据生成：`PYTHONPATH=$PWD /home/tiaozhansai/carla-driving-challenge/.venv/bin/python tools/pointcloud_p0/build_group_report.py`。

## 网页源码

`tools/pointcloud_p0/web/` 保存定位诊断、重叠点和方案 C 验收的三个网页源码。网页所引用的原始测试数据、报告 JSON 和图片仍存放在服务器的 `artifacts/runtime/`，并未包含在代码提交中。重建验收网页数据可运行 `build_group_report.py`，再将相应网页源码放到生成的数据目录并通过本地 HTTP 服务访问。
