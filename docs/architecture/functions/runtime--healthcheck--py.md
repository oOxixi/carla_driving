# healthcheck：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[runtime/healthcheck.py](../../../runtime/healthcheck.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Structured preflight for interfaces, Qwen, CARLA and local dependencies.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

<a id="fn--http-json"></a>

### `_http_json`

源码位置：[runtime/healthcheck.py 第 22 行](../../../runtime/healthcheck.py#L22)。类型：`FunctionDef`。

```python
_http_json(url: str, timeout_s: float) -> tuple[bool, dict[str, Any] | None, str]
```

对给定 URL 以 timeout_s 执行 GET 并解析 JSON，返回可达性及载荷/错误证据；HTTP/URL/超时/JSON 错误归入失败结果。JSON 根类型未单独保证为 mapping，下游不能把注解当作验证。

<a id="fn--interfaces"></a>

### `_interfaces`

源码位置：[runtime/healthcheck.py 第 36 行](../../../runtime/healthcheck.py#L36)。类型：`FunctionDef`。

```python
_interfaces() -> dict[str, Any]
```

加载7个接口示例并通过 InterfaceRegistry 校验，记录 Schema 文件 SHA256；这里是原始文件字节哈希，不是规范化 contract hash。捕获校验/读取错误用于健康报告。

<a id="fn--dependencies"></a>

### `_dependencies`

源码位置：[runtime/healthcheck.py 第 53 行](../../../runtime/healthcheck.py#L53)。类型：`FunctionDef`。

```python
_dependencies() -> dict[str, Any]
```

依次尝试导入 carla/numpy/PIL/onnxruntime/jsonschema/torch/transformers；前五项为required，后两项非required。发行版版本查询与可导入性分开，onnxruntime-gpu版本缺失不必然代表onnxruntime导入失败。

<a id="fn--carla"></a>

### `_carla`

源码位置：[runtime/healthcheck.py 第 82 行](../../../runtime/healthcheck.py#L82)。类型：`FunctionDef`。

```python
_carla(host: str, port: int, timeout_s: float) -> dict[str, Any]
```

导入 CARLA client、连接给定host/port并读取world/map/actor数量，异常转UNAVAILABLE诊断。不会tick、加载地图或改变场景，但确实访问运行中的服务。

<a id="fn-run-healthcheck"></a>

### `run_healthcheck`

源码位置：[runtime/healthcheck.py 第 104 行](../../../runtime/healthcheck.py#L104)。类型：`FunctionDef`。

```python
run_healthcheck(*, qwen_url: str, carla_host: str, carla_port: int, timeout_s: float, require_qwen: bool, require_carla: bool) -> dict[str, Any]
```

综合接口、依赖、CARLA、Qwen健康信息；即使 require_carla/require_qwen 为False仍执行探测，仅最终门禁不同。require_qwen 检查production_ready；require_carla关闭不取消required依赖中的carla导入要求（客户端安装和服务在线是两回事）。

<a id="fn-main"></a>

### `main`

源码位置：[runtime/healthcheck.py 第 143 行](../../../runtime/healthcheck.py#L143)。类型：`FunctionDef`。

```python
main() -> int
```

CLI默认Qwen URL http://127.0.0.1:8765、CARLA host127.0.0.1/port2000、timeout3秒；require开关默认False，output默认None。执行探测、可选写JSON并打印，overall通过返回0，否则1；文档整理不会运行此实时探测。

## 内部调用与异常路径

- `_http_json` 调用：`error.read`, `json.loads`, `response.read`, `type`, `urlopen`.
- `_interfaces` 调用：`InterfaceRegistry`, `example_path.read_text`, `hashlib.sha256`, `hashlib.sha256(schema_path.read_bytes()).hexdigest`, `json.loads`, `records.append`, `registry.validate`, `schema_path.read_bytes`, `schema_path.relative_to`, `sorted`, `str`.
- `_dependencies` 调用：`__import__`, `all`, `package_version`, `type`.
- `_carla` 调用：`carla.Client`, `client.get_world`, `client.set_timeout`, `len`, `type`, `world.get_actors`, `world.get_map`.
- `run_healthcheck` 调用：`_carla`, `_dependencies`, `_http_json`, `_interfaces`, `checks['qwen'].get`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `failures.append`, `qwen_url.rstrip`, `type`.
- `main` 调用：`argparse.ArgumentParser`, `args.output.parent.mkdir`, `args.output.write_text`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`, `run_healthcheck`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 145 行：`parser.add_argument('--qwen-url', default='http://127.0.0.1:8765')`。
- 第 146 行：`parser.add_argument('--carla-host', default='127.0.0.1')`。
- 第 147 行：`parser.add_argument('--carla-port', type=int, default=2000)`。
- 第 148 行：`parser.add_argument('--timeout-s', type=float, default=3.0)`。
- 第 149 行：`parser.add_argument('--require-qwen', action='store_true')`。
- 第 150 行：`parser.add_argument('--require-carla', action='store_true')`。
- 第 151 行：`parser.add_argument('--output', type=Path)`。

## 上下游与关联验证

静态导入的项目内实现：

- [runtime/interface_registry.py](../../../runtime/interface_registry.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-runtime-healthcheck-py"></a>

### `runtime/healthcheck.py`

来源 SHA256：`ebeb1b0042df7d4861535c26990402c733ae00c9d2587a94a9a9b8c67df60f0d`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 145 | `'--qwen-url'` | `default='http://127.0.0.1:8765'` |
| 146 | `'--carla-host'` | `default='127.0.0.1'` |
| 147 | `'--carla-port'` | `type=int; default=2000` |
| 148 | `'--timeout-s'` | `type=float; default=3.0` |
| 149 | `'--require-qwen'` | `action='store_true'` |
| 150 | `'--require-carla'` | `action='store_true'` |
| 151 | `'--output'` | `type=Path` |
