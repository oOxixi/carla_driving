# benchmark_control_runtime：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/benchmark_control_runtime.py](../../../tools/benchmark_control_runtime.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Measure D validation and final safety arbitration without CARLA I/O.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `percentile`

源码位置：[tools/benchmark_control_runtime.py 第 17 行](../../../tools/benchmark_control_runtime.py#L17)。类型：`FunctionDef`。

```python
percentile(values: list[float], q: float) -> float
```

【percentile】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `load_example`

源码位置：[tools/benchmark_control_runtime.py 第 26 行](../../../tools/benchmark_control_runtime.py#L26)。类型：`FunctionDef`。

```python
load_example(name: str) -> dict
```

【load_example】从参数、文件、环境或缓存解析维护工具的数据检查、生成、评测或证据处理所需输入；路径优先级、默认值和缺失处理以函数体为准，读取成功不自动证明内容身份正确。

### `main`

源码位置：[tools/benchmark_control_runtime.py 第 30 行](../../../tools/benchmark_control_runtime.py#L30)。类型：`FunctionDef`。

```python
main() -> int
```

【main】是维护工具的数据检查、生成、评测或证据处理的执行/命令入口；参数来自紧邻签名或本页CLI表，可能读取外部资源、写产物或启动服务，应以退出码、原始日志和固定输入身份判定结果。

## 内部调用与异常路径

- `percentile` 调用：`int`, `len`, `min`, `sorted`.
- `load_example` 调用：`(ROOT / 'interfaces' / 'examples' / f'{name}.json').read_text`, `json.loads`.
- `main` 调用：`DControlRuntime`, `ValueError`, `argparse.ArgumentParser`, `args.output.parent.mkdir`, `args.output.write_text`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `int`, `json.dumps`, `latencies.append`, `load_example`, `max`, `parser.add_argument`, `parser.parse_args`, `percentile`, `print`, `range`, `runtime.apply`, `runtime.complete`, `statistics.fmean`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 36 行：`ValueError('frames must be at least 100')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 32 行：`parser.add_argument('--output', required=True, type=Path)`。
- 第 33 行：`parser.add_argument('--frames', type=int, default=10000)`。

## 上下游与关联验证

静态导入的项目内实现：

- [car_control_D/control_runtime.py](../../../car_control_D/control_runtime.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/benchmark_control_runtime.py`

来源 SHA256：`4f6bc5a1fbac140934cd77d553053b2d113db7bce3ff6338ba14890955c47407`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 32 | `'--output'` | `required=True; type=Path` |
| 33 | `'--frames'` | `type=int; default=10000` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `main` / 36 | `args.frames < 100` | `raise ValueError('frames must be at least 100')` |
