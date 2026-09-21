# frozen_text_hash：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/frozen_text_hash.py](../../../tools/frozen_text_hash.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Stable checksums for frozen, text-only validation artifacts.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `canonical_crlf_bytes`

源码位置：[tools/frozen_text_hash.py 第 8 行](../../../tools/frozen_text_hash.py#L8)。类型：`FunctionDef`。

```python
canonical_crlf_bytes(raw: bytes) -> bytes
```

Return text bytes with every newline represented as CRLF.

Frozen benchmark and RTX 5070 manifests were originally published from a
Windows checkout.  Normalizing before hashing preserves those published
digests while making verification independent of checkout policy.

### `frozen_text_sha256`

源码位置：[tools/frozen_text_hash.py 第 20 行](../../../tools/frozen_text_hash.py#L20)。类型：`FunctionDef`。

```python
frozen_text_sha256(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `canonical_crlf_bytes` 调用：`normalized.replace`, `raw.replace`, `raw.replace(b'\r\n', b'\n').replace`.
- `frozen_text_sha256` 调用：`Path`, `Path(path).read_bytes`, `canonical_crlf_bytes`, `hashlib.sha256`, `hashlib.sha256(canonical_crlf_bytes(Path(path).read_bytes())).hexdigest`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_repro_delivery.py](../../../integration/tests/test_repro_delivery.py)
- [tools/benchmark_audit.py](../../../tools/benchmark_audit.py)
- [tools/promote_reference_run.py](../../../tools/promote_reference_run.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/frozen_text_hash.py`

来源 SHA256：`cf8f786bc01a2ea43b9d30879bd6c91179112afce2d1a69bb52e72463bdcce35`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
