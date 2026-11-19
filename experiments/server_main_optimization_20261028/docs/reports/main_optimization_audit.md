# main_optimization 优化审计

## 基线与原则

- 冻结基线：`origin/main@a05c8b76efcd4c176965223c661f40b153cb1836`。
- 本分支从该 SHA 直接创建，未改写 `main`。
- 不针对某一个已通过场景调 A/B/C/D 控制参数，不把延迟或准确率代理结果写成正式成绩。
- 优化集中在模型身份、决策输入准确性、失败关闭、可操作性和可审计性。

## 发现并解决的问题

| 问题 | 风险 | 处理 |
|---|---|---|
| 正式 runner 默认 Qwen3.5-2B，但远程 profile 仍默认旧 GPTQ | 不同入口实际使用不同模型 | 建立唯一生产 profile，固定 model、revision、artifact 指纹、224 图像和 64 token |
| 返回 token 与 logprob 不对应时借用首个 logprob | 错误置信度可能被当成可信决策 | token 不匹配立即失败关闭，并增加反例测试 |
| 多目标拼图只按距离选两个目标 | 语音点名的较远目标可能不进入重点画面 | 明确语义目标优先，再按距离和置信度排序 |
| 健康检查只看 production-ready | 错模型、错 revision、错模式也可能放行 | 严格核对 exact model、revision、artifact、planner_v2 与 CARLA |
| S2/S3 启动脚本只检查连通或“名称含 2B” | 无法证明正式模型与服务模式 | 正式运行前执行严格健康门禁并保存 JSON |
| Qwen 服务与 runtime 测试未被默认 pytest 收集 | 局部服务回归可能被隐藏 | 纳入 pytest testpaths，并恢复可嵌入 HTTP server 工厂 |
| 文档仍描述“简单命令不调用 Qwen” | 与当前全指令 Qwen 合同冲突 | 统一场景说明、技术方案和远程运行手册 |
| 缺少一次命令的评委验收入口 | 现场证据分散、难复查 | 新增静态/在线一键验收，输出 JSON 与 Markdown |
| 普通 LiDAR 障碍限速被当前车速二次截断 | 红灯停车后限速被锁为 0，即使转绿也无法起步 | 限速改为由可用制动距离计算的安全速度上限，短时遮挡继续保留该正值上限 |
| 所有 C 侧限速都被记录成 VRU | 普通障碍与行人/非机动车证据无法区分 | 根据 `source_by_field` 分别记录动态障碍与 VRU 限速来源及接管原因 |
| 断点恢复用 `z=0` 反查二维路线点 | Town03_Opt 叠层道路可能选中下层道路，导致高度跳变、偏航和无意义重规划 | 使用 Route Manager 保存的三维路线高程作投影提示，并在路线重建和传感器预热期间保持制动 |
| 普通 Qwen 计划没有保留临时机动路线 | 车道标签函数仍无条件计算路线偏差，首条 `KEEP_LANE` 计划会解引用空路线并终止闭环 | 仅在显式回归原车道步骤中计算保留路线偏差；普通计划直接采用当前语义车道标签，并增加空路线回归测试 |
| 合法返回原车道被最近车道中心跳变误判 | S2 P3 返回步骤中，CARLA 最近车道中心瞬时产生 3.3～4.6 m 偏移；D 在不知道当前步骤已获授权的情况下持续制动并限制转向，形成零速死锁 | 将“已应用轨迹的当前横向步骤”作为显式安全上下文传给 D；只豁免普通车道偏移/压线告警，碰撞、TTC、障碍物、红灯、watchdog 与严重路线偏差继续失败关闭 |
| 坡道纵断面被 LiDAR 当成近距障碍 | Town03_Opt 陡坡转平处的路面进入固定传感器高度窗，三车道同时出现约 5 m 假目标并永久停车 | 在近场 0.5 m 前向切片中校验垂直结构或紧凑横向结构；薄且横跨车道的路面回波被剔除，远场稀疏目标继续沿用点数门禁 |

## 当前生产模型合同

| 字段 | 值 |
|---|---|
| profile | qwen3.5-2b |
| model | Qwen/Qwen3.5-2B |
| exact revision | 15852e8c16360a2fea060d615a32b45270f8a8fc |
| artifact SHA-256 | 4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa |
| protocol | planner_v2 / ManeuverPlan V2 |
| visual budget | 224 x 224 / 64 tokens |

旧 Qwen3-VL GPTQ/FP8 仅保留为 RTX 5070 历史诊断资料，不能用于新的正式证据。

## 静态与单元验证

本分支修改后已完成：

- `python -m pytest -q`：1194 passed，4 skipped（本机可选依赖跳过）。
- `python tools/validate_scenarios.py`：155 checked，0 failed。
- `python tools/validate_official_scenes.py`：S1、S2、S3 全部 PASS。
- PowerShell 官方场景入口的 ValidateOnly：PASS。

这些结果证明代码、接口和场景合同未回归，不等于真实 CARLA 里程、真实 Qwen
准确率或正式延迟成绩。

## tiaozhansai CARLA 针对性闭环回归

2026-10-18 在 `tiaozhansai` 使用 CARLA 0.9.16、Town03_Opt 和
`main_optimization` 当前工作树执行了 1800 帧（90 秒仿真时间）的 S2 恢复段回归：

- 车辆两次在红灯停止线前停车，信号解除后均重新起步；第一次恢复后速度达到
  4.85 m/s，第二次恢复后达到 5.66 m/s。
- 141 帧普通 LiDAR 动态障碍限速均为正值，范围 6.82～10.16 m/s；未再出现
  停车后限速永久锁为 0 的状态。
- 普通障碍限速来源记录为 `C_FUSION_DYNAMIC_HAZARD_SPEED_CAP`，未误标为 VRU。
- 该段未发生碰撞或车道侵入，最大路线横向偏差为 0.54 m。
- 原始证据保存在服务器
  `artifacts/logs/S2_redlight_release_fix/`，包括 1800 帧 JSONL 和 summary。

该运行从 3500 m 恢复并限制为 90 秒，未到达后续 P4～P6 事件，因此完整 S2
验收按合同为 `FAILED`。这里仅将它作为“红灯停车后可恢复”和“动态限速来源正确”
的定向回归证据，不把它表述为完整 8 km 或 Qwen 全链路通过。

同日使用相同 3500 m 恢复点完成20秒断点对齐复测。恢复位姿明确记录为
`GLOBAL_ROUTE_3D`，首帧路线横向误差由旧实现约 1.93 m 降为 0.000043 m，整段最大
偏差为 0.0017 m，重规划次数由2次降为0。车辆从静止正常加速到约37.7 km/h，随后
在真实红灯停止线前停车；没有碰撞。原始证据位于服务器
`artifacts/logs/S2_resume_alignment_fix/`。该短测只证明断点重建和启动阶段对齐，
同样不作为完整 S2 成绩。

此外新增 `integration/tests/test_stop_release_gate.py`，统一覆盖普通 LiDAR 障碍、
短时遮挡、VRU 慢行和红灯解除四类“临时安全约束不能形成永久零速锁死”的跨模块门禁。

同日又以正式固定 Qwen3.5-2B、`planner_v2`、Town03_Opt 和全传感器模式执行
600 帧 S2 smoke。严格健康门禁逐项核对 model、revision、artifact、模式和 CARLA 后
通过；首条指令真实进入 Qwen，唯一终态为 `SUCCEEDED`，传感器到轨迹耗时约
195.1 ms。车辆在红灯前停车并在绿灯后恢复到约 38.7 km/h，0 碰撞、0 车道侵入，
最大路线偏差约 0.247 m。原始证据位于服务器
`artifacts/logs/S2_smoke_qwen2b_fix_20261018/`。该运行只到 30 秒，后五个阶段尚未触发，
所以完整场景验收失败是预期结果，不把 smoke 写成 8 km 通过。

随后一次完整 S2 运行在约 2.67 km 的 P3 返回原车道步骤暴露通用安全上下文缺口：
临时返回路线仍有效且控制器在继续收敛，但 CARLA 路口最近车道中心跳变导致
`lane_offset_m` 瞬时达到 3.3～4.6 m，D 连续输出 `LANE_OFFSET_TOO_LARGE` 制动，
车辆最终静止。该失败证据保存在服务器
`artifacts/logs/S2_full_qwen2b_20261018/`，没有删除或冒充通过记录。

2026-10-19 使用 `DEV_S2_P3_PEDESTRIAN_OVERTAKE_TARGETED` 对修复进行真实专项复测。
两条指令均由固定 Qwen3.5-2B 生成并以 `SUCCEEDED` 结束；车辆完成停车让行、左变道、
超越慢车、右变道返回以及恢复 40 km/h，最终 lane id 与初始 lane id 同为 `3`。
运行最大路线偏差 0.378 m、0 碰撞、无安全误刹停，Qwen、扩展和场景三层验收均
通过。原始证据位于服务器 `artifacts/logs/S2_P3_lane_crossing_fix_20261019/`。
该 450 m 夹具只作为 P3 缺陷的专项闭环证明；完整 8 km 仍使用官方场景独立验收。

随后完整 S2 在约 3.625 km 暴露另一项独立问题：路线误差仅约 0.004 m、附近没有
场景 Actor，但道路由约 -17° 陡坡快速变平，固定 LiDAR 高度窗把抬升的路面解释成
约 5.1 m 障碍，C 因此保持 `FOLLOWING` 零速。失败证据保存在服务器
`artifacts/logs/S2_full_lane_crossing_fix_20261019/`，没有删除。

2026-10-20 增加近场局部结构过滤并从 3.615 km 重建恢复段复测。车辆在真实红灯前
停车后重新起步，越过原 3.625 km 卡死点，并继续运行到约 4.115 km；最终仍以
5.48 m/s 行驶，0 碰撞，最大路线偏差 0.781 m（合同阈值 1.0 m）。原始证据位于服务器
`artifacts/logs/S2_grade_filter_resume_v2_20261020/`。该限帧恢复段按设计跳过前三条
已验证指令且没有跑完剩余路线，所以完整场景验收显示 `FAILED` 是预期结果；它仅证明
坡道误检及永久停车已解除，不能替代完整 8 km 成绩。

## 评委验收命令

仅检查仓库静态交付：

```bash
python tools/validate_judge_readiness.py
```

Qwen 与 CARLA 均启动后执行在线门禁：

```bash
python tools/validate_judge_readiness.py --require-live
```

正式报告位于 `artifacts/review/main_optimization_readiness.json` 及同名 Markdown。
正式提交时应同时保留各场景 runner 生成的原始 JSONL、场景结果和评分报告。

## 尚未冒充完成的工作

- 已有服务器定向 CARLA 回归，但尚未用本轮代码生成新的 S1/S2/S3 完整里程成绩。
- 当前分支没有声称模型准确率百分比提高；语义目标优先是可测试的输入改进，实际收益
  仍应在冻结数据和服务器闭环上比较。
- 服务器启动新代码后必须显式提交已核验的 revision 与 artifact 指纹，否则生产
  Qwen 服务拒绝启动。
