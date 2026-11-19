# tiaozhansai服务器代码与运行依赖盘点

2026-10-29初次只读盘点。下列HEAD和PID是当次快照，不是持续监控。
根目录统一为`/home/tiaozhansai/`。用户随后批准整理，6个历史目录已移入归档；
**当前目录和实际删除记录请以[整理后布局](SERVER_LAYOUT.md)为准**，下文保留原位置作审计对照。
当前运行代码/环境/模型路径未动，服务未重启。

## 服务器到底正在用哪份代码

| 用途 | 实际位置 | 当次证据 |
| --- | --- | --- |
| 现有Qwen规划适配器 | `carla-driving-main-optimization` | PID 6587，cwd在此，入口`python -m qwen_service.server`，18005 health=READY，planner_v2 |
| 真实2B模型推理 | `carla-driving-2B/.venv-qwen2b-cu130` + `carla-driving-2B/models/Qwen3.5-2B` | vLLM PID 2535027，8000 health HTTP 200；进程参数绑定该模型目录 |
| 新语义适配准备 | `carla-driving-qwen-semantic-adaptation` | 独立worktree/分支，训练未开始，未承接8000/18005服务 |
| 准备区软件测试解释器 | `carla-driving-challenge/.venv/bin/python` | 实际用于本阶段51项软件测试，未安装/升级包 |
| CPU tokenizer检查解释器 | `carla-driving-2B/.venv-qwen2b-cu130/bin/python` | 21条检查通过，无模型权重加载 |
| CARLA仿真服务 | `CARLA_0.9.16/runtime/CarlaUE4/Binaries/Linux/CarlaUE4-Linux-Shipping` | PID 1004317，独立仿真引擎进程；引擎存活不等于正在跑8km测试 |

关键限定：main_optimization磁盘HEAD是`f92ac6fcc`，但适配器进程在2026-10-26启动，之后没有重启。
其stdout落在`artifacts/validation/qwen_adapter_e3363dbe6_20261026.log`。
因此只能确认“服务从该工作区启动、磁盘现为f92”，**不能用当前HEAD冒充进程内存里已加载的精确提交**。
日志名也不是不可篡改的启动SHA证明。本次不为确认SHA而重启原服务。

健康接口仍报告固定模型`Qwen/Qwen3.5-2B`、revision
`15852e8c16360a2fea060d615a32b45270f8a8fc`、artifact
`4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`。
这是部署自报身份；本次没有重新全量计算模型fingerprint。

## 逐目录处置清单

| 目录 | 本地磁盘版本 | 分类 | 结论 |
| --- | --- | --- | --- |
| `carla-driving-main-optimization` | main_optimization / f92ac6fcc | 现有服务源目录和原方案 | 必须保留；既有outputs/也保留 |
| `carla-driving-qwen-semantic-adaptation` | qwen_semantic_adaptation / 本分支 | 当前新增开发 | 必须保留；后续本项只在这里改 |
| `carla-driving-2B` | candidate-2b-cu130 / 7348d18 | 老源码 + 正在使用的模型/环境 | 老源码不是当前适配器入口，但整目录绝不能删 |
| `carla-driving-challenge` | challenge / ca353478 | 独立Student/A3历史项目 + 当前测试venv | 不属本项；数据、权重、venv仍保留，不能整目录删 |
| `carla-driving-challenge-a3-v3` | a3/train-v3-robust / 18a95de9 | A3 V3历史训练worktree | 当前不承接语义服务；含权重与交接证据，保留 |
| `carla-driving-challenge-a3-prep` | detached / 525bd2fe | 早期A3准备worktree | 可列入归档候选；含旧基线权重，必须先确认交接和备份 |
| `carla-driving-main-verify-5413772` | main / 06f5816 | 旧基础赛道验证worktree | 当前不是主服务目录，可列入归档候选，先保留验证证据 |
| `carla-main-verify-runtime-5413772` | 非Git，含carla/soundfile包 | 旧运行时目录 | 当前challenge venv的carla来自自身site-packages，但未做全系统引用审计；不能据此直接删旧运行时 |
| `carla-driving-scene` | scene_organized / f4bb5499 + 大量未提交修改 | 旧场景开发worktree | 不作为新任务开发入口；必须先保存diff、未跟踪文件和artifact，不能当垃圾删 |
| `CARLA_0.9.16` | 非Git运行包 | 活动仿真依赖 | 必须保留 |

远端快照：GitHub main=a05c8b76，main_optimization=f92ac6fcc，challenge=2da949be。
服务器旧challenge目录仍在ca353478，**不是GitHub最新challenge**。不将本项整理扩展为自动更新挑战赛道。
只对当前语义分支同步说明；其他同事分支不合并、不删除，历史A3工作区只改变归档位置。

## 哪些算“完全淘汰”

当前证据只支持区分“活动依赖”“历史工作区”“未晋升实验”，不支持宣布任何一个完整服务器目录可无条件删除。

- 已停止作为推进方案：sequence_first、clause_focused、中文协议替代、当前受限thinking诊断；代码/证据保留。
- 不是当前主代码：旧scene、旧main-verify、早期A3 prep。但未运行不等于可删除，尤其存在未提交改动和模型资产。
- 仍然使用，不能误删：2B模型/venv、challenge测试venv、原main_optimization、CARLA运行包。
- `tools/run_qwen3vl_2b_vllm_cu132.sh`针对另一套Qwen3-VL INT4/FP8配置，不是本机当前Qwen3.5-2B启动入口。
  不应拿它重启当前服务；但它可能供其他环境复现，本次不跨范围删除。
- 可另行清理的候选：传输用`.tar`/`.bundle`、Python/pytest缓存、已核实有相同哈希归档的重复artifact。
  尚未逐件核实、列出删除目标或去重；训练best/last/candidate文件用途不同，不能因文件名相似就删。

## 后续进一步删除或迁移时的边界

1. 对每个明确目录检查cwd、已打开文件、venv/PYTHONPATH、脚本引用和worktree关系。
2. 对dirty scene保存提交或可恢复补丁，并保全未跟踪文件；ignored权重/日志必须另备份。
3. 对A3包和权重先核对SHA256、交接manifest与独立备份，避免把唯一正式资产当临时文件。
4. 先可恢复归档，不直接递归删除；普通Git worktree须用相应worktree流程，不能破坏共享Git元数据。
5. 环境/模型迁移单独安排服务窗口，验证新路径再停用旧路径；本轮不迁移任何活动环境/模型。

本清单是初次决策依据，已执行的可恢复归档和缓存清理由SERVER_LAYOUT.md记载；不代表可以继续永久删除资产。
