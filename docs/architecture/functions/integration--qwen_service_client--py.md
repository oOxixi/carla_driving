# qwen_service_client：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[integration/qwen_service_client.py](../../../integration/qwen_service_client.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Client for the repository-owned bounded Qwen inference service.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

<a id="fn-qwenserviceclient"></a>

### `QwenServiceClient`

源码位置：[integration/qwen_service_client.py 第 17 行](../../../integration/qwen_service_client.py#L17)。类型：`ClassDef`。

此 integration 类服务旧版 QwenInputContext → {status,request_id,decision} 协议。与 qwen_service.client.QwenServiceClient 同名但不兼容；carla_runner 的 canonical 编排实际导入后者，维护时必须核对完整导入路径。

<a id="fn-qwenserviceclient---init--"></a>

### `QwenServiceClient.__init__`

源码位置：[integration/qwen_service_client.py 第 18 行](../../../integration/qwen_service_client.py#L18)。类型：`FunctionDef`。

```python
QwenServiceClient.__init__(self, base_url: str, *, timeout_s: float=5.0) -> None
```

base_url 必须是无 query/fragment 的绝对 HTTP(S) URL；timeout_s 默认 5 秒且须有限正数。仅保存参数，不发网络请求；这是 HTTP 等待时限，不是模型计划 deadline。

<a id="fn-qwenserviceclient-infer"></a>

### `QwenServiceClient.infer`

源码位置：[integration/qwen_service_client.py 第 36 行](../../../integration/qwen_service_client.py#L36)。类型：`FunctionDef`。

```python
QwenServiceClient.infer(self, context: QwenInputContext) -> dict[str, Any]
```

要求 QwenInputContext，将 to_payload 序列化 POST /infer；响应须 status=READY、request_id 与输入一致、decision 为映射，再调用 validate_qwen_response。服务错误/身份错配/非法决策抛异常，不自动重试，不返回 canonical DecisionPlan/ManeuverPlan。

<a id="fn-qwenserviceclient-health"></a>

### `QwenServiceClient.health`

源码位置：[integration/qwen_service_client.py 第 62 行](../../../integration/qwen_service_client.py#L62)。类型：`FunctionDef`。

```python
QwenServiceClient.health(self) -> dict[str, Any]
```

GET /health 并返回 JSON 对象；此函数不判定 production_ready 是否为真，健康门禁须由调用方消费字段。

<a id="fn-qwenserviceclient-metrics"></a>

### `QwenServiceClient.metrics`

源码位置：[integration/qwen_service_client.py 第 65 行](../../../integration/qwen_service_client.py#L65)。类型：`FunctionDef`。

```python
QwenServiceClient.metrics(self) -> dict[str, Any]
```

GET /metrics 并返回 JSON 对象，不聚合统计，也不对指标键做 Schema 校验。

<a id="fn-qwenserviceclient--get"></a>

### `QwenServiceClient._get`

源码位置：[integration/qwen_service_client.py 第 68 行](../../../integration/qwen_service_client.py#L68)。类型：`FunctionDef`。

```python
QwenServiceClient._get(self, route: str) -> dict[str, Any]
```

以配置 timeout_s 发 GET 到相对 endpoint，委托 _open/_response_json；共享 HTTP 错误处理，不创建缓存。

<a id="fn-qwenserviceclient--open"></a>

### `QwenServiceClient._open`

源码位置：[integration/qwen_service_client.py 第 72 行](../../../integration/qwen_service_client.py#L72)。类型：`FunctionDef`。

```python
QwenServiceClient._open(self, request: Request) -> HTTPResponse
```

urllib 打开请求。HTTPError 尝试读取服务错误 JSON 并抛 RuntimeError，URLError 转为服务不可达 RuntimeError；超时等其他异常可继续向上传播。错误 JSON 路径假定可用 .get，不能保证任意服务错误体都保持统一异常类型。

<a id="fn--response-json"></a>

### `_response_json`

源码位置：[integration/qwen_service_client.py 第 87 行](../../../integration/qwen_service_client.py#L87)。类型：`FunctionDef`。

```python
_response_json(response: HTTPResponse) -> dict[str, Any]
```

读取并 UTF-8 解码 JSON，finally 关闭 response；非法 JSON 或非对象结果抛 RuntimeError。仅结构检查，不检查具体业务字段。

## 内部调用与异常路径

- `_response_json` 调用：`RuntimeError`, `isinstance`, `json.loads`, `response.close`, `response.read`, `response.read().decode`.
- `__init__` 调用：`ValueError`, `base_url.rstrip`, `base_url.strip`, `float`, `isinstance`, `math.isfinite`, `type`, `urlsplit`.
- `infer` 调用：`Request`, `RuntimeError`, `TypeError`, `_response_json`, `context.to_payload`, `isinstance`, `json.dumps`, `json.dumps(context.to_payload(), ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode`, `payload.get`, `self._open`, `validate_qwen_response`.
- `health` 调用：`self._get`.
- `metrics` 调用：`self._get`.
- `_get` 调用：`Request`, `_response_json`, `self._open`.
- `_open` 调用：`RuntimeError`, `error.read`, `error.read().decode`, `json.loads`, `payload.get`, `urlopen`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 20 行：`ValueError('base_url must be a non-empty string')`。
- `__init__`，第 23 行：`ValueError('base_url must be an absolute HTTP(S) URL')`。
- `__init__`，第 25 行：`ValueError('base_url must not contain a query or fragment')`。
- `__init__`，第 32 行：`ValueError('timeout_s must be finite and positive')`。
- `_open`，第 82 行：`RuntimeError(f'Qwen service {code}: {message}')`。
- `_open`，第 84 行：`RuntimeError(f'Qwen service unavailable: {error.reason}')`。
- `_response_json`，第 91 行：`RuntimeError('Qwen service returned invalid JSON')`。
- `_response_json`，第 95 行：`RuntimeError('Qwen service response must be a JSON object')`。
- `infer`，第 38 行：`TypeError('context must be QwenInputContext')`。
- `infer`，第 54 行：`RuntimeError('Qwen service returned a non-ready response')`。
- `infer`，第 56 行：`RuntimeError('Qwen service response request_id mismatch')`。
- `infer`，第 59 行：`RuntimeError('Qwen service response has no decision object')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)

静态 import 消费者（含测试）：

- [integration/scenario_runner_agent.py](../../../integration/scenario_runner_agent.py)
- [qwen_service/tests/test_server.py](../../../qwen_service/tests/test_server.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-qwen-service-client-py"></a>

### `integration/qwen_service_client.py`

来源 SHA256：`8823858138ae9643c585458d203b2187f47e506099d59f50ae7c7d9501337c0f`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `QwenServiceClient.__init__` / 20 | `type(base_url) is not str or not base_url.strip()` | `raise ValueError('base_url must be a non-empty string')` |
| `QwenServiceClient.__init__` / 23 | `parsed.scheme not in {'http', 'https'} or not parsed.netloc` | `raise ValueError('base_url must be an absolute HTTP(S) URL')` |
| `QwenServiceClient.__init__` / 25 | `parsed.query or parsed.fragment` | `raise ValueError('base_url must not contain a query or fragment')` |
| `QwenServiceClient.__init__` / 32 | `type(timeout_s) not in (int, float) or isinstance(timeout_s, bool) or (not math.isfinite(float(timeout_s))) or (float(timeout_s) <= 0.0)` | `raise ValueError('timeout_s must be finite and positive')` |
| `QwenServiceClient.infer` / 38 | `not isinstance(context, QwenInputContext)` | `raise TypeError('context must be QwenInputContext')` |
| `QwenServiceClient.infer` / 54 | `payload.get('status') != 'READY'` | `raise RuntimeError('Qwen service returned a non-ready response')` |
| `QwenServiceClient.infer` / 56 | `payload.get('request_id') != context.request_id` | `raise RuntimeError('Qwen service response request_id mismatch')` |
| `QwenServiceClient.infer` / 59 | `not isinstance(decision, Mapping)` | `raise RuntimeError('Qwen service response has no decision object')` |
| `QwenServiceClient._open` / 82 | `except HTTPError` | `raise RuntimeError(f'Qwen service {code}: {message}') from error` |
| `QwenServiceClient._open` / 84 | `except URLError` | `raise RuntimeError(f'Qwen service unavailable: {error.reason}') from error` |
| `_response_json` / 91 | `except (UnicodeDecodeError, json.JSONDecodeError)` | `raise RuntimeError('Qwen service returned invalid JSON') from error` |
| `_response_json` / 95 | `not isinstance(payload, dict)` | `raise RuntimeError('Qwen service response must be a JSON object')` |
