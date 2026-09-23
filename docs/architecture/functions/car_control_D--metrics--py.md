# metrics：功能记录

上级模块：[模块说明](../modules/vehicle-safety.md) · 实现：[car_control_D/metrics.py](../../../car_control_D/metrics.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [C/D分工与实时仲裁](longitudinal-safety-contract.md)
- [安全覆盖的生命周期影响](control-frame.md)

## 功能职责与范围

metrics

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `ScenarioRecorder`

源码位置：[car_control_D/metrics.py 第 10 行](../../../car_control_D/metrics.py#L10)。类型：`ClassDef`。

面向开发/离线场景的内存加文件记录器，分别保存 event、frame、command，并委托 `OfficialScorer` 生成汇总。它没有 schema、锁、轮转或运行身份冻结，不能单独作为正式比赛证据链。

### `ScenarioRecorder.__init__`

源码位置：[car_control_D/metrics.py 第 11 行](../../../car_control_D/metrics.py#L11)。类型：`FunctionDef`。

```python
ScenarioRecorder.__init__(self, log_dir: str | Path='logs') -> None
```

创建 `log_dir`（默认相对当前工作目录的 `logs`），初始化三个空列表。构造不会清理既有 JSONL，因此内存只含本实例新记录，而磁盘追加文件可能含历史运行。

### `ScenarioRecorder.log_event`

源码位置：[car_control_D/metrics.py 第 17 行](../../../car_control_D/metrics.py#L17)。类型：`FunctionDef`。

```python
ScenarioRecorder.log_event(self, event_type: str, **fields: Any) -> None
```

把 `event_type` 与任意字段合成字典，先追加内存再追加 `event_log.jsonl`。若文件写入失败，内存已发生变化；传入 fields 中同名 `event_type` 会因字典展开顺序覆盖形参值。

### `ScenarioRecorder.log_frame`

源码位置：[car_control_D/metrics.py 第 22 行](../../../car_control_D/metrics.py#L22)。类型：`FunctionDef`。

```python
ScenarioRecorder.log_frame(self, **fields: Any) -> None
```

将任意 frame 字段字典保存到内存并追加 `frame_log.jsonl`。没有必需 frame/time/control 字段校验，也没有复制后冻结嵌套值；调用方负责单位和运行身份。

### `ScenarioRecorder.log_command`

源码位置：[car_control_D/metrics.py 第 26 行](../../../car_control_D/metrics.py#L26)。类型：`FunctionDef`。

```python
ScenarioRecorder.log_command(self, command: Dict[str, Any]) -> None
```

把传入 command 字典引用放入内存，并追加写 `command_log.jsonl`。不经 command schema 验证；后续修改原字典可能改变内存视图但不会改变已写磁盘行。

### `ScenarioRecorder.write_result`

源码位置：[car_control_D/metrics.py 第 30 行](../../../car_control_D/metrics.py#L30)。类型：`FunctionDef`。

```python
ScenarioRecorder.write_result(self, result: Dict[str, Any]) -> Dict[str, Any]
```

覆盖写 `result.json` 并原样返回输入字典。没有追加历史、原子替换或结果 schema 校验，多场景共用目录时只保留最后一次 result 文件。

### `ScenarioRecorder.write_score_report`

源码位置：[car_control_D/metrics.py 第 34 行](../../../car_control_D/metrics.py#L34)。类型：`FunctionDef`。

```python
ScenarioRecorder.write_score_report(self, scenario_results: List[Dict[str, Any]]) -> Dict[str, Any]
```

用给定 scenario results 和本实例全部 command 记录生成汇总，覆盖写 `score_report.json` 并返回报告。该报告实现仓库内 25/10/5 基线规则，不绑定官方版本、提交或输入哈希。

## 内部调用与异常路径

- `__init__` 调用：`ensure_dir`.
- `log_event` 调用：`append_jsonl`, `self.events.append`.
- `log_frame` 调用：`append_jsonl`, `self.frames.append`.
- `log_command` 调用：`append_jsonl`, `self.commands.append`.
- `write_result` 调用：`write_json`.
- `write_score_report` 调用：`OfficialScorer`, `OfficialScorer().summarize`, `write_json`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_D/event_logger.py](../../../car_control_D/event_logger.py)
- [car_control_D/official_score.py](../../../car_control_D/official_score.py)

静态 import 消费者（含测试）：

- [car_control_D/demo_fake_integration.py](../../../car_control_D/demo_fake_integration.py)
- [car_control_D/scenario_runner.py](../../../car_control_D/scenario_runner.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-safety.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_D/metrics.py`

来源 SHA256：`a7bdd671c3465e1bda94a5aefcd29ceb90c857a94402b1de1d9ddda0942d1857`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
