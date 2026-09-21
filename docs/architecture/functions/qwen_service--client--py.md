# client：功能记录

上级模块：[模块说明](../modules/support-qwen.md) · 实现：[qwen_service/client.py](../../../qwen_service/client.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [服务模式、动作组装与health](qwen-service-semantics.md)

## 功能职责与范围

Strict stdlib client suitable for runtime.PipelineOrchestrator.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `QwenServiceClient`

源码位置：[qwen_service/client.py 第 14 行](../../../qwen_service/client.py#L14)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenServiceClient.__init__`

源码位置：[qwen_service/client.py 第 15 行](../../../qwen_service/client.py#L15)。类型：`FunctionDef`。

```python
QwenServiceClient.__init__(self, base_url: str='http://127.0.0.1:8765', *, timeout_s: float=0.35, request_transform: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenServiceClient.infer`

源码位置：[qwen_service/client.py 第 32 行](../../../qwen_service/client.py#L32)。类型：`FunctionDef`。

```python
QwenServiceClient.infer(self, request: Mapping[str, Any]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenServiceClient.health`

源码位置：[qwen_service/client.py 第 77 行](../../../qwen_service/client.py#L77)。类型：`FunctionDef`。

```python
QwenServiceClient.health(self) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenServiceClient.metrics`

源码位置：[qwen_service/client.py 第 81 行](../../../qwen_service/client.py#L81)。类型：`FunctionDef`。

```python
QwenServiceClient.metrics(self) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenServiceClient.pop_timing`

源码位置：[qwen_service/client.py 第 85 行](../../../qwen_service/client.py#L85)。类型：`FunctionDef`。

```python
QwenServiceClient.pop_timing(self, request_id: str) -> dict[str, float] | None
```

Return and retire client-side timing for one completed request.

### `QwenServiceClient.__call__`

源码位置：[qwen_service/client.py 第 90 行](../../../qwen_service/client.py#L90)。类型：`FunctionDef`。

```python
QwenServiceClient.__call__(self, request: Mapping[str, Any]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `__init__` 调用：`Lock`, `TypeError`, `ValueError`, `base_url.rstrip`, `callable`, `float`.
- `infer` 调用：`Request`, `RuntimeError`, `dict`, `error.read`, `json.dumps`, `json.dumps(dict(payload), ensure_ascii=False, allow_nan=False).encode`, `json.loads`, `request.get`, `response.read`, `self.request_transform`, `str`, `time.perf_counter_ns`, `urlopen`.
- `health` 调用：`json.loads`, `response.read`, `urlopen`.
- `metrics` 调用：`json.loads`, `response.read`, `urlopen`.
- `pop_timing` 调用：`self._timings.pop`.
- `__call__` 调用：`self.infer`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 28 行：`ValueError('timeout_s must be positive')`。
- `__init__`，第 30 行：`TypeError('request_transform must be callable or None')`。
- `infer`，第 73 行：`RuntimeError(f'Qwen service {error.code}: {payload}')`。
- `infer`，第 75 行：`RuntimeError(f'Qwen service unavailable: {error.reason}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [tools/run_acceptance_suite_a800.py](../../../tools/run_acceptance_suite_a800.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-qwen.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `qwen_service/client.py`

来源 SHA256：`f517ba029b9138369bb537b94d3fc833ca265e17acdaafbe152275b1446ee58b`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `QwenServiceClient.__init__` / 28 | `self.timeout_s <= 0` | `raise ValueError('timeout_s must be positive')` |
| `QwenServiceClient.__init__` / 30 | `request_transform is not None and (not callable(request_transform))` | `raise TypeError('request_transform must be callable or None')` |
| `QwenServiceClient.infer` / 73 | `except HTTPError` | `raise RuntimeError(f'Qwen service {error.code}: {payload}') from error` |
| `QwenServiceClient.infer` / 75 | `except URLError` | `raise RuntimeError(f'Qwen service unavailable: {error.reason}') from error` |
