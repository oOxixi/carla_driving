# B3 HIL 回放、测量与证据

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [Adapter能力、时钟域与测量范围](../functions/hil-trace-semantics.md)

上级：[挑战赛道](../modules/challenge.md)。

## 功能分组

代码目录：[hil](../../../challenge/hil)。

| 功能 | 实现 |
|---|---|
| 命令行、三类 Runtime 适配 | cli.py、runtime_adapter.py |
| 时钟标记、分段、统计、轮次、硬件采样 | stages.py、rounds.py、samplers.py |
| 候选身份、Git/hash、来源与产物 | identity.py、provenance.py、artifact.py |
| 冻结请求、回放、结构/一致性检查 | freeze.py、replay.py、consistency.py、contract.py |
| CSV/JSON 列、文件读写与证据包 | columns.py、run_io.py、schemas/ |
| 长稳、失败案例、报告与交接 | stability.py、failure_cases.py、report.py、handoff.py |

InProcessStudentRuntime 复用 A1 模型/预处理/Adapter，可带 PlanValidator；OnnxModelRuntime 使用 ORT 和宿主 Adapter，但不验证 Plan；BoardCliRuntime 调子进程，以 stdin 一条 ModelRequest、stdout 最后一行 JSON 计划交互，可携带 trace。板端格式详见 [a4_runtime_contract.md](../../../challenge/hil/a4_runtime_contract.md)。

## 测量和身份

阶段由 stages.py 的 STAGES 唯一定义：input_arrival、preprocess_end、packing_end、inference_start、inference_end、postprocess_end、adapter_end、plan_ready。时间为高分辨率 perf_counter_ns，不能混用板端和宿主时钟域。warmup 与 measured 分离，READY 记录参与延时汇总；错误、超时、缺标记应明确报告，不能以缺测当作零耗时。

身份字段为 git_sha、model_id、model_sha256、dataset_version、config_id；随机权重结构测试必须带随机初始化说明。report/evidence 不等于部署 Gate；model-only 指标不包括真实 PlanValidator 成本。冻结、hard-case 和 soak 均应保留输入、候选和环境身份。

## 已确认问题

1. runtime_adapter.py:546 在宿主先 mark(input_arrival)，576-584 随后把板端 trace 全部再次 mark；完整板端 trace 带 input_arrival 时与 stages.py:133-134 的重复检查冲突。595 又 mark(plan_ready)，会重复板端末标记。即使不重复，也有混用时钟域风险，应分离 host envelope 和 board trace。
2. runtime_adapter.py:284-321 的 verify_consistency 重新执行 preprocessor/model/decode/validate，与 StudentBackend 比较；没有调用实际被测 self.infer。因此不能证明实际埋点路径与 Backend 一致。
3. OnnxModelRuntime:377-380 声明 full_chain=True、plan_validator=False，431-436 对未经计划验证的输出标为 READY；这与“model-only”说明并存。消费者应依据能力字段判定，后续需要统一 full_chain/READY 的含义。

以上为静态审查事实及对应风险，没有声称板端已实测失败。

## 测试与修改联动

[hil/tests](../../../challenge/hil/tests) 覆盖 stages、contract、identity/io、artifact、provenance/consistency、replay/failures、freeze/stability/handoff、report。新增板端完整 trace 回归应直接覆盖 BoardCliRuntime，不能仅用 FakeRuntime 代替适配器。

修改阶段需同步列定义/JSON schema、板端契约、采样器、报告和历史证据兼容策略；修改 Adapter/预处理时比较真实 infer 路径；修改 Gate/身份时联动 A3 候选、ONNX 元数据和 evidence manifest。


## 模块接口与参数核对（2026-09-20）

PlannerRuntime.infer(request,case_id,round_index,phase)返回(plan或None,StageTrace)。capabilities的full_chain/model_only/plan_validator/stage_source共同解释能力，READY不能替代这些字段。

### 参数语义与生效边界

phase默认measured，warmup应单独统计；BoardCliRuntime.timeout_s默认30s，check_runtime_contract.latency_budget_ms默认1000ms，二者不是同一门限。阶段时间为perf_counter_ns，不能拼接不同机器时钟。

### 上下游与修改影响

修改trace需联动阶段唯一性、collector/report及失败记录。BoardCli重复mark、consistency绕过self.infer等已知问题见AUDIT；本轮静态记录不等于硬件验收。

### [challenge/hil/runtime_adapter.py](../../../challenge/hil/runtime_adapter.py) 的入口与声明

```python
RuntimeCapabilities.to_dict(self) -> dict[str, Any]
PlannerRuntime.infer(self, request: Mapping[str, Any], *, case_id: str, round_index: int, phase: str='measured') -> tuple[Mapping[str, Any] | None, StageTrace]
PlannerRuntime.close(self) -> None
state_dict_fingerprint(model: Any) -> str
InProcessStudentRuntime.__init__(self, repo_root: str | Path, *, weights: str | Path | None=None, weights_manifest: str | Path | None=None, dataset_version: str=UNRESOLVED, seed: int | None=20260911) -> None
InProcessStudentRuntime.infer(self, request: Mapping[str, Any], *, case_id: str, round_index: int, phase: str='measured') -> tuple[Mapping[str, Any] | None, StageTrace]
InProcessStudentRuntime.verify_consistency(self, request: Mapping[str, Any]) -> dict[str, Any]
InProcessStudentRuntime.close(self) -> None
OnnxModelRuntime.__init__(self, repo_root: str | Path, onnx_path: str | Path) -> None
OnnxModelRuntime.infer(self, request: Mapping[str, Any], *, case_id: str, round_index: int, phase: str='measured') -> tuple[Mapping[str, Any] | None, StageTrace]
OnnxModelRuntime.bench_model_only(self, request: Mapping[str, Any], *, iterations: int=10, warmup: int=5, case_id: str='') -> list[StageTrace]
OnnxModelRuntime.close(self) -> None
BoardCliRuntime.__init__(self, command: str | Sequence[str], *, artifact: str | Path | None=None, model_id: str=UNRESOLVED, config_id: str=UNRESOLVED, dataset_version: str=UNRESOLVED, timeout_s: float=30.0) -> None
BoardCliRuntime.infer(self, request: Mapping[str, Any], *, case_id: str, round_index: int, phase: str='measured') -> tuple[Mapping[str, Any] | None, StageTrace]
BoardCliRuntime.close(self) -> None
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `RuntimeCapabilities.full_chain` | `bool` | `无声明默认（构造/赋值方提供）` |
| `RuntimeCapabilities.model_only` | `bool` | `无声明默认（构造/赋值方提供）` |
| `RuntimeCapabilities.plan_validator` | `bool` | `无声明默认（构造/赋值方提供）` |
| `RuntimeCapabilities.stage_source` | `str` | `无声明默认（构造/赋值方提供）` |
| `RuntimeCapabilities.notes` | `tuple[str, ...]` | `()` |
| `PlannerRuntime.name` | `str` | `无声明默认（构造/赋值方提供）` |
| `PlannerRuntime.identity` | `CandidateIdentity` | `无声明默认（构造/赋值方提供）` |
| `PlannerRuntime.capabilities` | `RuntimeCapabilities` | `无声明默认（构造/赋值方提供）` |

### [challenge/hil/stages.py](../../../challenge/hil/stages.py) 的入口与声明

```python
clock_resolution_ns() -> float
percentile(values: Iterable[float], quantile: float) -> float | None
summarize(values: Iterable[float]) -> dict[str, float | int | None]
StageTrace.mark(self, stage: str, timestamp_ns: int | None=None) -> int
StageTrace.finish(self, outcome: str, *, reason_code: str | None=None, detail: str | None=None) -> None
StageTrace.durations_ms(self) -> dict[str, float]
StageTrace.missing_stages(self) -> tuple[str, ...]
StageTrace.to_csv_row(self, *, run_id: str, identity: Mapping[str, str], wall_time_utc: str | None=None) -> dict[str, Any]
StageTrace.to_dict(self) -> dict[str, Any]
LatencyCollector.__init__(self) -> None
LatencyCollector.add(self, trace: StageTrace) -> None
LatencyCollector.traces(self) -> tuple[StageTrace, ...]
LatencyCollector.report(self, *, run_id: str, identity: Mapping[str, str]) -> dict[str, Any]
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `StageTrace.trace_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `StageTrace.case_id` | `str` | `''` |
| `StageTrace.round_index` | `int` | `0` |
| `StageTrace.phase` | `str` | `'measured'` |
| `StageTrace.clock_ns` | `Callable[[], int]` | `time.perf_counter_ns` |
| `StageTrace.timestamps_ns` | `dict[str, int]` | `field(default_factory=dict)` |
| `StageTrace.outcome` | `str &#124; None` | `None` |
| `StageTrace.reason_code` | `str &#124; None` | `None` |
| `StageTrace.outcome_detail` | `str &#124; None` | `None` |
| `StageTrace.stage_source` | `str` | `'INSTRUMENTED'` |
| `StageTrace.clock_domain` | `str` | `'monotonic_host'` |

### [challenge/hil/contract.py](../../../challenge/hil/contract.py) 的入口与声明

```python
check_runtime_contract(runtime: PlannerRuntime, requests: Sequence[Mapping[str, Any]], *, latency_budget_ms: float=1000.0) -> dict[str, Any]
```

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [challenge/hil/__init__.py](../functions/challenge--hil--__init__--py.md)
- [challenge/hil/artifact.py](../functions/challenge--hil--artifact--py.md)
- [challenge/hil/cli.py](../functions/challenge--hil--cli--py.md)
- [challenge/hil/columns.py](../functions/challenge--hil--columns--py.md)
- [challenge/hil/consistency.py](../functions/challenge--hil--consistency--py.md)
- [challenge/hil/contract.py](../functions/challenge--hil--contract--py.md)
- [challenge/hil/failure_cases.py](../functions/challenge--hil--failure_cases--py.md)
- [challenge/hil/freeze.py](../functions/challenge--hil--freeze--py.md)
- [challenge/hil/handoff.py](../functions/challenge--hil--handoff--py.md)
- [challenge/hil/identity.py](../functions/challenge--hil--identity--py.md)
- [challenge/hil/provenance.py](../functions/challenge--hil--provenance--py.md)
- [challenge/hil/replay.py](../functions/challenge--hil--replay--py.md)
- [challenge/hil/report.py](../functions/challenge--hil--report--py.md)
- [challenge/hil/requirements.txt](../functions/challenge--hil--requirements--txt.md)
- [challenge/hil/rounds.py](../functions/challenge--hil--rounds--py.md)
- [challenge/hil/run_io.py](../functions/challenge--hil--run_io--py.md)
- [challenge/hil/runtime_adapter.py](../functions/challenge--hil--runtime_adapter--py.md)
- [challenge/hil/samplers.py](../functions/challenge--hil--samplers--py.md)
- [challenge/hil/stability.py](../functions/challenge--hil--stability--py.md)
- [challenge/hil/stages.py](../functions/challenge--hil--stages--py.md)

## 诊断与维护交接

本模块证据：原始trace、阶段次数、时钟域；重复mark见AUDIT A02，未硬件验收。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/tests/__init__.py`

来源 SHA256：`854fe6e48b83d44c93b63db7f26a2c64b40f1eda555b5b6ce064f3a3c39cd39c`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/hil/tests/fakes.py`

来源 SHA256：`6890559cf51a50231309fc9e82469a8175bf66e68981bd865c000e1374f6b137`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/hil/tests/test_artifact.py`

来源 SHA256：`0b531db2163656f7589c6a3fcf838837986db664204b3e60a15ac76564c31b3a`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/hil/tests/test_contract.py`

来源 SHA256：`02438fc7690d4443b60896eb230ebc81f5b25a5d034c23a48c094f69a1e6ad1e`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_CrashingRuntime.infer` / 67 | `本地无直接if；检查上下文` | `raise RuntimeError('boom')` |
### `challenge/hil/tests/test_freeze_stability_handoff.py`

来源 SHA256：`cc43be4316e319ee248d74de893491330e21dc64ef78fac2ac6a5f111069311f`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/hil/tests/test_identity_and_io.py`

来源 SHA256：`613fd79e0b7c213fe0bf868c0f1d897889a125a8e7816a6d12fa992e104232ec`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/hil/tests/test_provenance_and_consistency.py`

来源 SHA256：`b98e21f3213f6bdc39e8b3501a279dc86806efb0c33163b93620e920953859b0`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_FakeSource.outputs` / 53 | `isinstance(value, Exception)` | `raise value` |
### `challenge/hil/tests/test_replay_and_failures.py`

来源 SHA256：`ba3cb58e6e8ecd9d0c41ae18f258f4ca056c01983850f157855471f79b723112`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/hil/tests/test_report.py`

来源 SHA256：`41c3922d8c7413f2cc3881a4545afa8fc7982b0130fc3e9f4434aac9707d222c`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `challenge/hil/tests/test_stages.py`

来源 SHA256：`b0b2ea5b0a669d8c5f08b01bb3336d92bd884c68febd6eacdc84c99caa0c9502`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
