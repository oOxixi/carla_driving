# build_submission_package：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/build_submission_package.py](../../../tools/build_submission_package.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Check release inputs and render the raw-backed Qwen 2B reproduction guide.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[tools/build_submission_package.py 第 12 行](../../../tools/build_submission_package.py#L12)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `check_release`

源码位置：[tools/build_submission_package.py 第 20 行](../../../tools/build_submission_package.py#L20)。类型：`FunctionDef`。

```python
check_release(root: Path) -> list[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `render_handoff`

源码位置：[tools/build_submission_package.py 第 41 行](../../../tools/build_submission_package.py#L41)。类型：`FunctionDef`。

```python
render_handoff(reference: Path, output: Path) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/build_submission_package.py 第 102 行](../../../tools/build_submission_package.py#L102)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `sha256_file` 调用：`digest.hexdigest`, `digest.update`, `hashlib.sha256`, `iter`, `path.open`, `stream.read`.
- `check_release` 调用：`any`, `item.is_file`, `missing.append`, `path.is_dir`, `path.is_file`, `path.rglob`, `path.stat`, `required.items`.
- `render_handoff` 调用：`(reference / 'metrics/accuracy.json').read_text`, `(reference / 'metrics/latency.json').read_text`, `(reference / 'metrics/scenarios.json').read_text`, `json.loads`, `output.parent.mkdir`, `output.write_text`.
- `main` 调用：`'\n- '.join`, `Path`, `argparse.ArgumentParser`, `args.root.resolve`, `check.add_argument`, `check_release`, `parser.add_subparsers`, `parser.parse_args`, `print`, `render.add_argument`, `render_handoff`, `sub.add_parser`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 106 行：`check.add_argument('--root', type=Path, default=Path('.'))`。
- 第 108 行：`render.add_argument('--reference-run', type=Path, default=Path('metrics/reference_5070'))`。
- 第 109 行：`render.add_argument('--output', type=Path, default=Path('docs/reproduction/QWEN2B_REPRODUCTION.md'))`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_repro_delivery.py](../../../integration/tests/test_repro_delivery.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/build_submission_package.py`

来源 SHA256：`15fb0ec5f1abfcbdd4927144f28bfd69e24db86e94d9942ef4771251be132619`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 106 | `'--root'` | `type=Path; default=Path('.')` |
| 108 | `'--reference-run'` | `type=Path; default=Path('metrics/reference_5070')` |
| 109 | `'--output'` | `type=Path; default=Path('docs/reproduction/QWEN2B_REPRODUCTION.md')` |
