# 服务器整理后的目录与恢复说明

2026-10-29执行；开发分支沿用用户确认的`qwen_semantic_adaptation`。
只整理历史工作区、零散传输文件和缓存，未修改当前运行方案的源码、配置、模型或环境路径。

## 项目相关主目录

```text
/home/tiaozhansai/
├── carla-driving-main-optimization/          原服务/驾驶方案；原路径不变
├── carla-driving-qwen-semantic-adaptation/  当前语义适配开发；原路径不变
├── carla-driving-2B/                        现用模型/环境与保留的7B历史源码
├── carla-driving-challenge/                 Student资产与当前测试环境
├── CARLA_0.9.16/                           现用仿真引擎
└── carla-archive/
    └── 20261029-layout/
        ├── worktrees/                      6个历史工作区/旧运行包/旧审计目录
        ├── transfers/                      历史bundle和patch
        ├── logs/                           未被进程打开的历史log/out
        ├── launchers/                      3个旧.codex启动脚本
        ├── scene_uncommitted.patch          scene的额外补丁副本
        ├── regenerable_caches.tar.gz       删除前的缓存备份
        └── manifest.json                   路径、哈希、Git状态、进程及health核验
```

此树只列项目主体，不是整个home的完整清单。`miniforge3`、`snap`、`carlaCache`和隐藏系统目录没有动。
`live_carla_viewer.py`、`S2_lane_test.json`、Miniforge安装器未处理。
`carla_town03_targeted_20261021.log`仍被CARLA进程使用，因此留在原位置，不能为了整齐移动它。

## 已归档的旧目录

以下目录从home顶层整体移到`carla-archive/20261029-layout/worktrees/`，文件内容保留：

| 原目录名 | 内容与保护 |
| --- | --- |
| `carla-driving-challenge-a3-prep` | 早期A3准备、权重和证据；使用git worktree move，登记已更新 |
| `carla-driving-challenge-a3-v3` | A3 V3训练、权重和证据；使用git worktree move，登记已更新 |
| `carla-driving-main-verify-5413772` | 旧main验证源码及证据，HEAD保持06f5816 |
| `carla-driving-scene` | 旧scene源码，HEAD保持f4bb5499；51条Git状态记录原样保留，含未提交/未跟踪内容 |
| `carla-main-verify-runtime-5413772` | 旧carla/soundfile运行包，未删内容 |
| `server_cleanup_audit_20260911` | 上一轮清理审计和备份，未删内容 |

历史命令中的旧绝对路径需参考本表换成归档路径；未为保留旧名称而在home创建6个兼容软链接。
没有改写历史脚本或原服务启动配置。当前使用的所有路径仍在原处。

## 删除了什么

- 实际删除的是归档工作区中67个未跟踪的`__pycache__`/`.pytest_cache`目录，逻辑大小13,157,581字节，约13MB。
- 删除前已打包并核验缓存内容，可从`regenerable_caches.tar.gz`恢复；正常也可通过重跑Python/pytest生成。
- 另有73个home零散文件仅移动，不是永久删除；每个文件记录移动前后SHA256。
- 没有永久删除历史源码、模型、best/last/candidate权重、数据、原始证据或scene未提交修改。
- 没有把未晋升的语义实验当作死代码删掉：它们仍被测试、对照实验和保护集检查引用。

减少的是home顶层工作区/文件杂乱，不是把唯一的历史资产当垃圾删除，也不声称释放了归档源码占用的磁盘。

## 7B方案明确保留

旧7B方案仍在原`/home/tiaozhansai/carla-driving-2B/`，未搬移或删除：

- `integration/day20/README.md`、`carla_rgb_qwen_closed_loop.py`、`qwen_vl_adapter.py`。
- `integration/day22/README.md`、`qwen_runtime.py`、`run_day22_qwen_runtime.py`。
- `qwen_service/model_card.md`、`models/README.md`。

这8个关键文件额外记录SHA256并逐项比对；该旧工作区其他受检源码也保持不变。
保留不等于启用：当前仍是固定Qwen3.5-2B，原生产profile不因整理而增加或切换7B。
本次检查的模型目录只有Qwen3.5-2B；没有下载、加载或宣称已保全本机不存在的7B权重。

## 不影响当前方案的核验

| 检查 | 结果 |
| --- | --- |
| main_optimization受检源码/配置 | 859个文件哈希、HEAD和Git状态整理前后相同 |
| 旧2B工作区受检源码/配置 | 727个文件哈希、HEAD和Git状态相同 |
| challenge受检源码/配置 | 1574个文件哈希、HEAD和Git状态相同 |
| 历史工作区 | 目录inode、受检源码哈希、HEAD和Git状态相同；仅清理未跟踪缓存 |
| 服务与CARLA | PID 6587/2535027/1004317及进程启动标识相同，未重启 |
| 健康状态 | 8000 HTTP 200；18005 HTTP 200、READY，2B身份未变 |
| 语义准备区软件测试 | 51 passed |

源码哈希检查不包含模型权重、第三方依赖、数据集和生成证据的全量内容；这些路径未被本次操作修改。
没有为目录整理重跑8km、调用新推理或启动训练，软件测试不冒充驾驶/模型通过证明。

## 需要恢复时

先停下对应历史任务，确认旧位置不存在，再按manifest中的`old`/`new`路径反向移动。
两个A3附加worktree必须由`carla-driving-challenge`执行`git worktree move <归档路径> <原路径>`，
不可只改目录名而遗漏Git登记。其他独立旧仓库/旧运行包可整体移回，保留其中`.git`和ignored资产。
不要删除或移动`carla-driving-challenge/.git/worktrees`，它仍管理归档中的A3工作区。

原始scene修改就在归档仓库里，无需先应用补丁；`scene_uncommitted.patch`仅是额外保险副本，不能重复应用。
缓存如需恢复，应先检查tar清单，再从归档根目录定向恢复；不覆盖当前活动代码。

完整私有证据位于服务器归档的`manifest.json`；本机副本位于
`artifacts/semantic_sft/server_layout_20261029/manifest.json`，不提交源码仓库。
