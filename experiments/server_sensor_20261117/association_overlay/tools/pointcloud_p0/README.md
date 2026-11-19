# P0 三维定位与逐点核查

代码位于独立工作树，不接入现有驾驶控制。YOLO 模型和学生、教师权重没有修改。

## 正式算法与离线真值隔离

integration/target_pointcloud_localization.py 只使用同步 RGB、普通 LiDAR、Radar、车辆位姿：将点云投影到检测框；相互重叠的框只保留独占点；用 RANSAC 地面平面去除地面附近点；对剩余点按距离自适应连通聚类；对于多个不易区分的簇返回 UNKNOWN；根据雷达投影和三维近邻支持选择簇。雷达必须投影到该目标唯一的检测框，减小串车风险。输出簇中心、最近和 P10 表面水平距离、前向最小值、点数、点范围、10%～90% 分布宽度。分布宽度不是已校准的概率置信区间。

正式算法不读取 Actor 真值、语义 LiDAR 的 Actor 编号、角色或真值包围盒。run_matrix.py 中的 evaluate 在预测完成后才读取真值。它用投影框 IoU ≥ 0.3 做一对一匹配；用同位置同帧语义 LiDAR 的近邻点（容差 0.08m）核查普通 LiDAR 点的命中 Actor 编号；语义匹配不了的点单独统计。Radar 使用扩展 0.2m 的 Actor 包围盒作近似核对；落盒外或多盒重合标为无法确认。被漏检或无法定位的车辆进入统计分母，不进入误差分布。

center_error 计算可见点簇中心到 Actor 包围盒中心的三维差。它包含可见车身表面到车身中心的系统偏移，并非估计车辆中心的精度。nearest_surface_range_error 是最近激光点的水平距离减去自车中心到二维 Actor 包围盒的最近水平距离，并非雷达距离误差。rear_longitudinal_error 是最小前向激光点位置减去 Actor 包围盒的最小前向位置，适用于本次同向平直道路。聚类中心输出的第二维是左正；xyz_min_ego / xyz_max_ego 原始范围采用 CARLA 右正，网页显示时已换成左正。

## 数据与口径

结果在服务器：
- pointcloud_p0_rear_final_20261117：11 类条件，每类 5 次；55 次、170 辆预期车次，其中两类使用项目默认 32 线；近距离的真值最近车身表面距离约 5.63～9.93m。
- pointcloud_p0_radar_compare_final_20261117：5 个相同遮挡帧的前后雷达关联对照。
- pointcloud_p0_20261117：网页，引用上述数据。
- pointcloud_p0_before_partial_occlusion_20261117、pointcloud_p0_weather_mixed_20261117 等为修订前记录，不参与最终统计。

前九类除稀疏组 16 线外，均使用 64 线高密度传感器；默认配置 32 线 / 224000 点每秒中、远距离各单独补测 5 次。每次使用同一 Town05 路段、Tesla Model 3、静态车辆；同条件 5 次只改变前后位置，不能当作独立道路或车型泛化验证。部分遮挡是同车道遮挡车横向偏移 0.9m。雨、雾和夜间的 CARLA 天气改变 RGB，不能证明 LiDAR/Radar 在真实雨雾中的物理表现。传感器与天气参数保存在每次 result.json；原始 LiDAR、语义 LiDAR、Radar 和相机图像保存在各自目录。所有定位仅使用单帧；不能把结果等同于此前原系统的多帧融合表现。

summary.json 中的定位百分比以预期车辆为分母，检出框匹配精度以检测框为分母；非标准 mAP。误差 P50/P95 仅统计已匹配且已定位车辆，数值附样本量。未提供正式验收阈值，因此不能把实验统计直接称作通过。sensitivity.json 是对现有样本做最少点数的事后筛选，不是独立验证，不作为部署阈值。

运行回归测试：
PYTHONPATH=$PWD python -m pytest -q integration/tests/test_target_pointcloud_localization.py integration/tests/test_pointcloud_p0_audit.py integration/tests/test_target_lane_association.py
