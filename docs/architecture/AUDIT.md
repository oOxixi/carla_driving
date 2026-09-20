# 全项目一致性审计台账

返回[项目导航](README.md)。基线 `fe1ba839`，日期 2026-09-20。
本轮交付为全量功能导航、静态接口核对和定点复现。以下业务问题尚未修复；不能把文档完成视为项目已无矛盾。

## 已确认问题

| ID / 优先级 | 触发与影响 | 代码证据 | 本轮验证 | 修复与联动范围 |
|---|---|---|---|---|
| A01 / 高 | 晋级检查仅绑定 Teacher 与 dataset_version，另一个 Student 的评测身份可被接受，无法证明成绩属于当前候选 | [artifacts.py](../../challenge/distillation/artifacts.py) 130–149 | 调用 `_validate_evaluation_identity`，传入不同 weights_sha256/model_id/config_id，仍正常返回；只复现身份校验，不宣称完整错误模型已部署 | A3 evaluate/promote/artifacts、候选 manifest、A1 后端；绑定 Student 权重和配置、Validation 清单身份，增加错配拒绝测试 |
| A02 / 高 | BoardCliRuntime 收到完整 trace 时与宿主重复 input_arrival；包含 plan_ready 也会重复，采样异常退出 | [runtime_adapter.py](../../challenge/hil/runtime_adapter.py) 546、576–595；[stages.py](../../challenge/hil/stages.py) 130–144 | mock subprocess 返回 trace，真实 `BoardCliRuntime.infer` 抛 `StageOrderError: stage already marked: input_arrival` | A4 trace 协议、B3 Adapter/stages/report；分开宿主 E2E 与板端阶段时间，不能混用两台机器 monotonic 时钟 |
| A03 / 中 | HIL consistency 重新实现推理并比较 Backend，没有执行实际带埋点的 self.infer；不能覆盖 A02 | [runtime_adapter.py](../../challenge/hil/runtime_adapter.py) 284–321 | 静态调用核对 | 一致性检查应跨真实 Adapter Interface，比较 Plan 与 trace；保留可解释容差 |
| A04 / 高 | vLLM 后端 health 恒真，服务配置完成可被报告为 READY，不代表模型可达 | [service.py](../../qwen_service/service.py) 442、483–484、1344–1352 | 未初始化 client 的实例仍返回 True；未进行真实网络断连试验 | 区分配置完成、可达、模型身份匹配和生产 Gate；与 runtime healthcheck 和故障测试联动 |
| A05 / 中 | 旧 Qwen HTTP 测试导入已删除 create_server，无法收集；默认 pytest 未包含该目录 | [test_server.py](../../qwen_service/tests/test_server.py) 10；[server.py](../../qwen_service/server.py)；[pytest.ini](../../pytest.ini) | collect-only 实际 ImportError | 按当前 QwenHTTPServer/QwenDecisionService 改测试，再明确默认/扩展测试集合 |
| A06 / 中 | 旧全链脚本将 scripts 当根目录，模块查找及产物目录错误 | [run_full_pipeline.sh](../../scripts/run_full_pipeline.sh) 4、53、107、166 | 静态路径计算；本轮未启动后台服务 | 修根目录解析，核对入口参数已演进情况，增加从任意 cwd 启动的检查 |
| A07 / 低 | 同名测试在模块内定义两次，Python 后者覆盖前者 | [test_safety_state.py](../../car_control_C/tests/test_safety_state.py) 80、99 | AST 全量扫描确认；当前两段同体 | 删除重复副本或命名独立意图；不能将两个定义计为两个有效测试 |
| A08 / 中 | integration README 的“尚未接入图像检测”等表述与现行链不符 | [integration README](../../integration/README.md) 原第 102–103 行；[runner](../../integration/carla_runner.py) 检测器初始化与来源审计 | 代码与文字对照 | 已增加历史范围提示与当前导航；具体字段来源仍需根据 perception_mode/实际记录判断，不能全局宣称真值已消失 |
| A09 / 中 | 默认 pytest 范围不包含 challenge 与 qwen_service；全量测试有声学依赖缺失 | [pytest.ini](../../pytest.ini)、[evaluate_voice_audio.py](../../tools/evaluate_voice_audio.py) | 对全部 141 个 tracked test 文件 collect-only：1373 tests collected，3 errors；两项缺 soundfile，一项 A05 | 建明确测试矩阵和依赖层级；缺依赖与代码错误分别处理，不通过忽略失败制造“全绿” |

## 明确能力缺口与待证风险

| ID | 状态与事实 | 影响 / 后续验证 |
|---|---|---|
| R01 | [export_onnx.py](../../challenge/export/export_onnx.py) 37–46 始终新建随机模型，无训练权重加载参数 | A3 PT→部署 ONNX 尚未闭合。当前结构 ONNX 是已声明的 smoke 产物，不是训练权重导出错误 |
| R02 | [OnnxModelRuntime](../../challenge/hil/runtime_adapter.py) 声明 full_chain=True、plan_validator=False，输出 READY 前未走 PlanValidator | READY/full_chain 的消费者可能混淆“已执行”与“已验证”；需统一能力标志语义 |
| R03 | [student_x86.py](../../challenge/runtime/student_x86.py) 独立硬编码输入 Shape | 当前数值一致；改结构时有漂移风险。该脚本零输入测前向，不是生产 ModelRequest Runtime |
| R04 | [canonical_bridge.py](../../integration/canonical_bridge.py) 139–160 包含 50m 默认距离、框中心投影、非首目标速度补零 | 应标注估算/缺失与置信边界；不能当完整测量融合。canonical y-left 与 CARLA y-right 是有意转换，不误报符号错误 |
| R05 | [runner](../../integration/carla_runner.py) 5953–5959 在 D 后启动宽限期覆盖全制动 | 是安全方向的执行例外；文档“D 唯一最后写入”不能按字面泛化，需核对日志记录最终实际执行值 |
| R06 | [OrchestratorConfig](../../runtime/orchestrator.py) 与 [strategy](../../config/strategy.py) 有独立默认 | 属于配置漂移风险，不能仅凭重名字段强制合并；先确定场景覆盖优先级 |
| R07 | [D2 view builder](../../challenge/dataset/build_a3_d2_view.py) 固定 cohort 与 D2 v1.1 | D3 数据到位不代表此入口自动支持 D3；顶层来源版本与 metadata 派生视图版本是不同身份 |
| R08 | Qwen profile 默认与当前 Teacher manifest 不同，旧 pinned/报告仍含历史身份 | 按入口与 cohort 选择，不批量替换所有模型字符串；报告不能追溯套用新 revision |

## 容易误判为重复的合法分工

- 实时链由 `ControlRuntime → SafetySupervisor` 执行；`DControlRuntime` 是另一种 canonical 封装并用于 benchmark。应说明适用 Interface，不直接删其中一个。
- `CARLA-Language-Benchmark` 与 `CARLA_Language_Benchmark` 提供文件目录及可导入兼容包装，审计算法委托 `tools.benchmark_audit`，不是两套独立计分算法。
- `strategy_config.yaml` 与 `driving_policy.json` 有基础参数、转换和覆盖关系；统一的是生效来源与记录，不要求物理合成一文件。
- B1 分批 collector/build/release 脚本记录不同数据生产阶段；必须保留冻结可复现性，再决定是否抽公共实现。

## 验证记录与处理顺序

1. 先处理 A01/A02/A04：它们影响证据可信性、板端 Adapter 和服务可用性判断。
2. 再处理 A05/A06/A07/A09：恢复可执行入口、测试发现与自动回归。
3. 对 R01/R02/R03 明确训练到部署交付契约，再扩展能力，避免先拼出看似“全链”的结果。
4. 最后处理深层重构：runner 职责集中、配置来源收敛、B1 批次共用实现，先保持现有 Interface 与历史证据。

本轮原始输出：`artifacts/architecture_probes_20260920.json`、`artifacts/architecture_full_collect_20260920.txt`（本地诊断产物，不作为长期发布证据）。
本轮没有训练、重生成冻结数据或运行真实 CARLA/J6P。修复后应在本台账逐项补测试与版本，不直接删除旧结论。

## Wave2专项问题

原A01–A09为审计编号，不是ACC_A01等场景。新增W2-01–W2-06见[核查记录](functions/wave2-audit.md)：派生契约漂移、STOP目标契约、long首故障与运行证据缺口。业务问题尚未修复。

## 顺序精读新增记录

- **M01-01 / 已复现、未修复**：[sensor_stability](functions/integration--sensor_stability--py.md)的run_sensor_probe预热失败后，测量while不进入但执行else，将success=True。实际函数mock边界复现frames=3/startup_frames=1、wait_for_frame=False得到success=true/aligned_frames=0。影响probe结果与CLI返回码的可信性；修复需检查循环成功条件并覆盖启动失败/测量失败/成功。该发现不等于CARLA真实传感器必然失效。


### 第2模块：异步规划精读新增证据（2026-09-20，基线fe1ba839）

**M02-01 / 已复现、未修复：V2 parser严格性随输入类型不同。** [parse_maneuver_plan](functions/integration--qwen_plan_adapter--py.md#fn-parse-maneuver-plan)对字符串使用默认JSONDecoder，`'{"x":NaN}'`得到包含float NaN的dict；传`{"x": float("nan")}`则抛QwenPlanParseError。Infinity同样属于默认解码器常量入口（本轮执行复现针对NaN）。此证据只证明parser边界不一致；后续InterfaceRegistry仍用allow_nan=False拒绝，未证明完整计划能进入车辆执行。后续若修复，回归文本/bytes/Mapping、NaN/Infinity/-Infinity、正常计划及fence/尾随文本。

**M02-02 / 已复现、未修复：场景监控不能保证全命令均有终态。** [QwenScenarioMonitor.finalize](functions/integration--qwen_scenario_monitor--py.md#fn-qwenscenariomonitor-finalize)中single_terminal仅遍历terminal_counts已有项。登记one/two两条QWEN_PLAN（调用数2），只给one上报SUCCEEDED，报告仍passed=True且single_terminal=True。影响以该检查证明整组命令生命周期完整性的可信度；单命令执行成功仍可能成立，不等于全部场景验收失效。另由源码可见terminal与reason_prefix分别用存在性匹配，未保证同一事件；该项本轮仅静态核对。后续回归缺终态、重复终态、内部wait ID过滤、终态/原因跨事件匹配。

可复现代码（工作树根目录，普通Python；不需要CARLA或模型服务）：

```python
import math
from integration.qwen_plan_adapter import parse_maneuver_plan, QwenPlanParseError
from integration.qwen_scenario_monitor import QwenScenarioMonitor
assert math.isnan(parse_maneuver_plan('{"x":NaN}')["x"])
try:
    parse_maneuver_plan({"x": float("nan")})
except QwenPlanParseError:
    pass
else:
    raise AssertionError("mapping unexpectedly accepted NaN")
m = QwenScenarioMonitor({"route": "QWEN_PLAN", "min_calls": 2,
                         "max_calls": 2, "expected_terminal": "SUCCEEDED"})
for cid in ("one", "two"):
    m.record_routing("QWEN_PLAN", qwen_submitted=True, command_id=cid)
m.record_terminal("SUCCEEDED", command_id="one")
report = m.finalize().to_dict()
assert report["passed"] is True
assert report["observed"]["terminal_counts"] == {"one": 1}
```

以上断言记录**现状问题**，不是期望修复后的测试规范。本轮已执行同等调用得到NaN分支差异及缺终态仍passed=True；未修改业务代码或现有测试。
