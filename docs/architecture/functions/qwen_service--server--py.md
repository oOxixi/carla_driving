# server：功能记录

上级模块：[模块说明](../modules/support-qwen.md) · 实现：[qwen_service/server.py](../../../qwen_service/server.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [服务模式、动作组装与health](qwen-service-semantics.md)

## 功能职责与范围

Dependency-light HTTP server exposing /health, /infer and /metrics.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `QwenRequestHandler.server: QwenHTTPServer`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `_configure_low_latency_socket`

源码位置：[qwen_service/server.py 第 26 行](../../../qwen_service/server.py#L26)。类型：`FunctionDef`。

```python
_configure_low_latency_socket(connection: Any) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenHTTPServer`

源码位置：[qwen_service/server.py 第 30 行](../../../qwen_service/server.py#L30)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenHTTPServer.__init__`

源码位置：[qwen_service/server.py 第 33 行](../../../qwen_service/server.py#L33)。类型：`FunctionDef`。

```python
QwenHTTPServer.__init__(self, address: tuple[str, int], service: QwenDecisionService) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenRequestHandler`

源码位置：[qwen_service/server.py 第 38 行](../../../qwen_service/server.py#L38)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenRequestHandler.setup`

源码位置：[qwen_service/server.py 第 42 行](../../../qwen_service/server.py#L42)。类型：`FunctionDef`。

```python
QwenRequestHandler.setup(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenRequestHandler.do_GET`

源码位置：[qwen_service/server.py 第 49 行](../../../qwen_service/server.py#L49)。类型：`FunctionDef`。

```python
QwenRequestHandler.do_GET(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenRequestHandler.do_POST`

源码位置：[qwen_service/server.py 第 59 行](../../../qwen_service/server.py#L59)。类型：`FunctionDef`。

```python
QwenRequestHandler.do_POST(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenRequestHandler.log_message`

源码位置：[qwen_service/server.py 第 88 行](../../../qwen_service/server.py#L88)。类型：`FunctionDef`。

```python
QwenRequestHandler.log_message(self, format: str, *args: Any) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenRequestHandler._send`

源码位置：[qwen_service/server.py 第 95 行](../../../qwen_service/server.py#L95)。类型：`FunctionDef`。

```python
QwenRequestHandler._send(self, status: int | HTTPStatus, payload: Any) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `build_service`

源码位置：[qwen_service/server.py 第 105 行](../../../qwen_service/server.py#L105)。类型：`FunctionDef`。

```python
build_service(args: argparse.Namespace) -> QwenDecisionService
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[qwen_service/server.py 第 147 行](../../../qwen_service/server.py#L147)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_configure_low_latency_socket` 调用：`connection.setsockopt`.
- `build_service` 调用：`DeterministicPlannerV2Backend`, `DeterministicTestBackend`, `QwenDecisionService`, `QwenServiceConfig`, `UnavailableBackend`, `ValueError`, `VllmQwenPlannerBackend`, `backend_type`.
- `main` 调用：`QwenHTTPServer`, `argparse.ArgumentParser`, `build_service`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`, `server.serve_forever`, `server.server_close`, `service.close`, `service.health`.
- `__init__` 调用：`super`, `super().__init__`.
- `setup` 调用：`_configure_low_latency_socket`, `super`, `super().setup`.
- `do_GET` 调用：`self._send`, `self.server.service.health`, `self.server.service.metrics`.
- `do_POST` 调用：`error.to_dict`, `int`, `json.loads`, `self._send`, `self.headers.get`, `self.headers.get_content_type`, `self.rfile.read`, `self.server.service.infer`, `str`.
- `log_message` 调用：`json.dumps`, `print`.
- `_send` 调用：`int`, `json.dumps`, `json.dumps(payload, ensure_ascii=False, allow_nan=False).encode`, `len`, `self.end_headers`, `self.send_header`, `self.send_response`, `self.wfile.write`, `str`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `build_service`，第 114 行：`ValueError('--vllm-base-url currently requires --qwen-mode planner_v2')`。
- `build_service`，第 116 行：`ValueError('--vllm-model is required with --vllm-base-url')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 149 行：`parser.add_argument('--host', default='127.0.0.1')`。
- 第 150 行：`parser.add_argument('--port', type=int, default=8765)`。
- 第 151 行：`parser.add_argument('--model-path', type=Path)`。
- 第 152 行：`parser.add_argument('--vllm-base-url', help='existing OpenAI-compatible vLLM /v1 endpoint')`。
- 第 154 行：`parser.add_argument('--vllm-model', help='exact model id served by vLLM')`。
- 第 155 行：`parser.add_argument('--image-root', type=Path)`。
- 第 156 行：`parser.add_argument('--deterministic-test-backend', action='store_true', help='contract tests only; never production evidence')`。
- 第 158 行：`parser.add_argument('--qwen-mode', choices=('atomic_v1', 'planner_v2'), default='atomic_v1')`。
- 第 159 行：`parser.add_argument('--timeout-ms', type=float, default=300.0)`。
- 第 160 行：`parser.add_argument('--max-concurrency', type=int, default=1)`。
- 第 161 行：`parser.add_argument('--max-request-bytes', type=int, default=262144)`。
- 第 162 行：`parser.add_argument('--max-new-tokens', type=int, default=256, help='generation ceiling; Planner V2 needs enough room for strict JSON')`。
- 第 166 行：`parser.add_argument('--min-pixels', type=int, default=64 * 28 * 28)`。
- 第 167 行：`parser.add_argument('--max-pixels', type=int, default=256 * 28 * 28)`。
- 第 168 行：`parser.add_argument('--image-max-side', type=int, default=224)`。
- 第 169 行：`parser.add_argument('--jpeg-quality', type=int, default=75)`。

## 上下游与关联验证

静态导入的项目内实现：

- [qwen_service/service.py](../../../qwen_service/service.py)

静态 import 消费者（含测试）：

- [integration/tests/test_qwen_service.py](../../../integration/tests/test_qwen_service.py)
- [qwen_service/__main__.py](../../../qwen_service/__main__.py)
- [qwen_service/tests/test_server.py](../../../qwen_service/tests/test_server.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-qwen.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `qwen_service/server.py`

来源 SHA256：`02edd7cb10e3a3c960318f24c93084846b4bf92e8330960d84b71cf6cc47afc9`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `QwenRequestHandler.server` | `QwenHTTPServer` | `无声明默认；构造/赋值方提供` |

CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 149 | `'--host'` | `default='127.0.0.1'` |
| 150 | `'--port'` | `type=int; default=8765` |
| 151 | `'--model-path'` | `type=Path` |
| 152 | `'--vllm-base-url'` | `help='existing OpenAI-compatible vLLM /v1 endpoint'` |
| 154 | `'--vllm-model'` | `help='exact model id served by vLLM'` |
| 155 | `'--image-root'` | `type=Path` |
| 156 | `'--deterministic-test-backend'` | `action='store_true'; help='contract tests only; never production evidence'` |
| 158 | `'--qwen-mode'` | `choices=('atomic_v1', 'planner_v2'); default='atomic_v1'` |
| 159 | `'--timeout-ms'` | `type=float; default=300.0` |
| 160 | `'--max-concurrency'` | `type=int; default=1` |
| 161 | `'--max-request-bytes'` | `type=int; default=262144` |
| 162 | `'--max-new-tokens'` | `type=int; default=256; help='generation ceiling; Planner V2 needs enough room for strict JSON'` |
| 166 | `'--min-pixels'` | `type=int; default=64 * 28 * 28` |
| 167 | `'--max-pixels'` | `type=int; default=256 * 28 * 28` |
| 168 | `'--image-max-side'` | `type=int; default=224` |
| 169 | `'--jpeg-quality'` | `type=int; default=75` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `build_service` / 114 | `NOT (args.deterministic_test_backend) AND args.vllm_base_url is not None AND args.qwen_mode != 'planner_v2'` | `raise ValueError('--vllm-base-url currently requires --qwen-mode planner_v2')` |
| `build_service` / 116 | `NOT (args.deterministic_test_backend) AND args.vllm_base_url is not None AND not args.vllm_model` | `raise ValueError('--vllm-model is required with --vllm-base-url')` |
