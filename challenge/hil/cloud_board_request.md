# 云上 J6 板卡（HiL&SiL 平台）申请与接入清单

> 整理日期：2026-09-23。用途：B3 的 W16/W17/W18（真实 J6P 独立实测、三类场景闭环、30 分钟长稳）
> 需要一块可 SSH 的 J6P 板卡，本文件汇总"找谁要、要提供什么、拿到后怎么接、上去跑什么"。

## 1. 先说结论

1. **没有公开的自助申请入口**。已实测：`hil.horizon.auto`、`sil.horizon.auto`、`cloud.horizon.auto`、
   `soca.horizon.auto`、`board.horizon.auto`、`j6.horizon.auto` 等域名均无 DNS；
   OE 站与开发者社区站内也没有"云板卡申请"页面。
2. 社区里唯一可核对的云上使用记录是论坛帖
   [【征程6云上使用】已登录调度服务器，但分配板卡 10.8.0.2 SSH 连接超时](https://developer.horizon.auto/forum/13802)
   （2026-09-05，已解决），其中明确提到"申请页面"、"SOCA 云平台"、
   "调度服务器"与手册《HiL&SiL平台使用手册-用户版本v1》。
3. 对本赛道而言，申请通道应是**赛事组委会/地平线对接人**：赛事通知原文写明
   "目前赛事组委会正在统筹协调相关芯片资源，资源到位后将统一同步大家"。
4. **必须明确要 J6P**：论坛案例里分到的是"天准 TADC-J6E/M"，板型与本赛道的 J6P 不一致；
   J6E/M 的板端数字不能写成 J6P 成绩。

## 2. 申请时要提供的信息（可直接复制给对接人）

| 项目 | 内容 |
|---|---|
| 赛事/项目 | 挑战赛道"揭榜挂帅"（XH-202602）；报名时使用的 6 位内部编号 + 学校 + 项目名 + 负责人 |
| **目标板型** | **J6P**（若只能提供 J6E/M，请注明：量化/编译可在 x86 完成，但板端性能与资源数字必须以 J6P 为准） |
| 用途 | ① 部署 A4 的 Student Runtime（`ModelRequest`→`ManeuverPlan`）② OpenExplorer 编译产物上板运行 ③ `hrt_model_exec perf` 取 Latency/FPS ④ `hrt_ucp_monitor` 取 BPU/DDR/内存 ⑤ ≥30 分钟长稳 + recovery probe ⑥ Seen/Variant/Unseen 分组复测 |
| 软件版本 | PC 端已用 **OE 3.9.1**（CPU 镜像 `openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1`）验证通过；请在开通时告知板端 **OE / UCP / BSP / 固件** 版本 |
| 工作时段 | 建议 **2 个时段**：首轮 bring-up（编译产物上板 + 功能一致性），二轮正式测量（≥3 轮 + 30 分钟长稳 + 恢复探针）。单次至少连续 4 小时 |
| 网络要求 | SSH（22 端口）到分配板卡；若需跳板/白名单，请提供出网与端口要求 |
| 所需产出 | 板端原始日志（`hrt_model_exec` 输出、`hrt_ucp_monitor` 采样、trace），以及我们按 B3 口径整理的报告 |
| 联系人 | 组内负责人姓名 + 邮箱/手机（由组内确定，不在仓库中留存个人联系方式） |

## 3. 拿到时段后的接入步骤（依据论坛帖与官方手册）

1. 登录 **SOCA 云平台**，从 *SSH access* 下载本账号 **PEM 私钥**（`chmod 600`，**私钥不入库**）；
2. 用平台给出的命令登录**调度服务器**（帖中示例 `52.80.174.119`，以平台实际为准）；
3. 在调度服务器内执行 `source /etc/environment`；
4. `ssh -o ConnectTimeout=10 root@<分配板卡IP>`（帖中示例 `10.8.0.2`）；
5. 排障顺序：先 `ping <板卡IP>` 与 `ssh -o ConnectTimeout=10` 判断是"通道问题/板卡未开机"还是板卡内部问题
   —— 帖中同类故障最终由平台修复，不要自行放宽安全设置。

## 4. 上板后要跑的测量（对应 B3 交付物）

| 命令/动作 | 产出 | 对应 B3 文件 |
|---|---|---|
| `hrt_model_exec model_info/infer --enable_dump/perf --thread_num N --frame_count M` | Latency、FPS、精度 dump | `latency_raw.csv`、报告 §3 |
| `hrt_ucp_monitor -b -e bpu -d 1000`（批处理、只看 BPU、1 s 刷新） | BPU 占用率 | `utilization_raw.csv` |
| `hrt_ucp_monitor -b` | 内存/DDR | `memory_raw.csv`、`hardware_metrics_schema.md` |
| 循环推理 ≥30 分钟 + recovery probe | 稳定性与恢复 | `stability_logs/` |
| `hbm_infer`（X86 控板端 RPC，官方定位"更适合批量数据集评测"） | 批量精度对照 | 精度对照报告 |
| 我们的 `--adapter board` + `contract`（describe / batch / model-only） | 契约与身份核验 | `contract_report.json` |

注：官方 Latency 口径（`hbDNNInferV2` → `hbUCPWaitTaskDone`）对应 B3 的 `model_only_ms`；
完整 Planner E2E（T0→T7）仍需 B3 自己的口径，两者不可互相替代。

## 5. 相关网址汇总（均为 2026-09-23 实测可访问）

| 用途 | 网址 |
|---|---|
| OE 资源下载（需登录，含 3.9.1 全部 12 个文件） | https://oe.horizon.auto/download/oe |
| 官方参考模型 + J6P/J6M/J6B 部署指标（公开） | https://oe.horizon.auto/labs |
| 官方手册：板端评测 | https://doc.oe.horizon.auto/guide/model_deployment/board_evaluation.html |
| 官方手册：板端资源评估（BPU/DDR/内存） | https://doc.oe.horizon.auto/guide/model_deployment/board_resource_evaluation.html |
| 官方手册：`hrt_model_exec` | https://doc.oe.horizon.auto/guide/tools_guide/dnn_tools/hrt_model_exec.html |
| 官方手册：`hbm_infer` | https://doc.oe.horizon.auto/guide/tools_guide/dnn_tools/hbm_infer.html |
| 官方手册：X86 仿真（无板替代路径） | https://doc.oe.horizon.auto/guide/model_compile/x86_simulation.html |
| 官方手册：安装前准备（Ubuntu 22.04/Docker/容器要求） | https://doc.oe.horizon.auto/guide/env_install/pre-installation_preparation.html |
| 官方手册：软件安装（`docker load` / `run_docker.sh`） | https://doc.oe.horizon.auto/guide/env_install/software_installation.html |
| 社区帖：云上使用流程与排障 | https://developer.horizon.auto/forum/13802 |
| 社区搜索（关键词"云上"） | https://developer.horizon.auto/search?keyword=%E4%BA%91%E4%B8%8A |
| 社区博客：**没有 J6 板子时工具链能验证到哪一步**（与本项目处境一致） | https://developer.horizon.auto/blog/14105 |
| 官方 agent 技能包（量化/编译/UCP/板端监控） | https://github.com/HorizonRobotics/OE-Skills |
| 地平线生态邮箱（无对接人时的兜底） | BD_Ecosystem@horizon.auto |
| 赛事组委会邮箱（来自赛事通知邮件） | panxinze@dfmc.com.cn、tc-linyao@dfmc.com.cn |

## 6. 注意事项

- **板型不符要标注**：J6E/M 的结果只能写"替代验证"，不得作为 J6P 达标依据；
- **私钥保密**：PEM 私钥只放本机，权限 600，不提交仓库、不粘贴到对话里；
- **时段有限**：把上表 4 的测量编排成一条脚本，一次跑完（本目录已有 `--adapter board` 契约、
  `dump-tensors`、`contract` 三条路径检查可复用）；
- **不要为了跑通而放宽安全/看门狗**：遇到真实基础链问题按团队清单 §4.10 的
  `REPRODUCE → trace → 报告主负责人` 流程处理。
