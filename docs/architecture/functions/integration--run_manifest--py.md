# run_manifest：功能记录

上级模块：[模块说明](../modules/vehicle-entry.md) · 实现：[integration/run_manifest.py](../../../integration/run_manifest.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [一帧控制的实际顺序与执行值](control-frame.md)

## 功能职责与范围

Atomic lifecycle records for reproducible evidence runs.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `RunContext.run_id: str`；默认：`未在声明处设置`。
- `RunContext.root: Path`；默认：`未在声明处设置`。
- `RunContext.manifest_path: Path`；默认：`未在声明处设置`。
- `RunContext.metrics_dir: Path`；默认：`未在声明处设置`。
- `RunContext.logs_dir: Path`；默认：`未在声明处设置`。
- `RunContext.media_dir: Path`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

<a id="fn-runcontext"></a>

### `RunContext`

源码位置：[integration/run_manifest.py 第 13 行](../../../integration/run_manifest.py#L13)。类型：`ClassDef`。

保存一次运行的run_id及root/manifest/metrics/logs/media路径，frozen dataclass防止字段重新赋值，但不保护路径下文件。由begin_run构造，消费者使用这些路径写证据。

<a id="fn--write-atomic"></a>

### `_write_atomic`

源码位置：[integration/run_manifest.py 第 22 行](../../../integration/run_manifest.py#L22)。类型：`FunctionDef`。

```python
_write_atomic(path: Path, payload: dict[str, object]) -> None
```

将payload以UTF-8、ensure_ascii=False、indent=2序列化到原扩展名追加.tmp的同目录文件，再os.replace目标。不会创建父目录，也没有并发锁/fsync；同一目标的并发写入不能据此视为安全，JSON/文件系统异常向上传播。

<a id="fn-begin-run"></a>

### `begin_run`

源码位置：[integration/run_manifest.py 第 30 行](../../../integration/run_manifest.py#L30)。类型：`FunctionDef`。

```python
begin_run(output_root: Path, metadata: dict[str, object]) -> RunContext
```

用UTC秒时间戳和UUID前8位生成run_id，在output_root/runs/<run_id>创建metrics、logs、media（exist_ok=False）。写run_manifest.json：metadata先展开，再强制写run_id、started_at、RUNNING与failure_reason=None，因此metadata不能覆盖这些起始字段。返回RunContext；中途创建失败不回滚已建目录。

<a id="fn-finish-run"></a>

### `finish_run`

源码位置：[integration/run_manifest.py 第 57 行](../../../integration/run_manifest.py#L57)。类型：`FunctionDef`。

```python
finish_run(context: RunContext, status: str, failure_reason: str | None) -> None
```

读取现有manifest，以调用方传入的status/failure_reason覆盖原值，补UTC finished_at并原子替换。不校验status枚举、不检查已终结状态，重复调用会重写完成时间；调用方负责生命周期约束。

<a id="fn-update-run-metadata"></a>

### `update_run_metadata`

源码位置：[integration/run_manifest.py 第 69 行](../../../integration/run_manifest.py#L69)。类型：`FunctionDef`。

```python
update_run_metadata(context: RunContext, metadata: dict[str, object]) -> None
```

Atomically supplement immutable-at-start provenance after validation.

## 内部调用与异常路径

- `_write_atomic` 调用：`json.dumps`, `os.replace`, `path.with_suffix`, `temp.write_text`.
- `begin_run` 调用：`RunContext`, `_write_atomic`, `datetime.now`, `directory.mkdir`, `now.isoformat`, `uuid4`.
- `finish_run` 调用：`_write_atomic`, `context.manifest_path.read_text`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `json.loads`, `payload.update`.
- `update_run_metadata` 调用：`_write_atomic`, `context.manifest_path.read_text`, `json.loads`, `payload.update`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_run_manifest.py](../../../integration/tests/test_run_manifest.py)
- [tools/repro_cli.py](../../../tools/repro_cli.py)
- [tools/run_four_modal_full_chain.py](../../../tools/run_four_modal_full_chain.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-entry.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-run-manifest-py"></a>

### `integration/run_manifest.py`

来源 SHA256：`1d7804dea57ede16c0367720c5ddfd2ddab8cf329358d7b5d449914f9ac07993`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `RunContext.run_id` | `str` | `无声明默认；构造/赋值方提供` |
| `RunContext.root` | `Path` | `无声明默认；构造/赋值方提供` |
| `RunContext.manifest_path` | `Path` | `无声明默认；构造/赋值方提供` |
| `RunContext.metrics_dir` | `Path` | `无声明默认；构造/赋值方提供` |
| `RunContext.logs_dir` | `Path` | `无声明默认；构造/赋值方提供` |
| `RunContext.media_dir` | `Path` | `无声明默认；构造/赋值方提供` |

## metadata写入与保护边界

update_run_metadata读取JSON后直接payload.update(metadata)再原子替换，虽然docstring写“immutable-at-start provenance”，实现没有拒绝覆盖run_id/status/started_at。调用方须限制键；不要把该函数记录成强制不可变。finish_run也不验证终态枚举。
