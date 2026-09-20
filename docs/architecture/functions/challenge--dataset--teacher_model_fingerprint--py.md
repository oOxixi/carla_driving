# teacher_model_fingerprint：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/teacher_model_fingerprint.py](../../../challenge/dataset/teacher_model_fingerprint.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

teacher_model_fingerprint

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[challenge/dataset/teacher_model_fingerprint.py 第 13 行](../../../challenge/dataset/teacher_model_fingerprint.py#L13)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `build_manifest`

源码位置：[challenge/dataset/teacher_model_fingerprint.py 第 21 行](../../../challenge/dataset/teacher_model_fingerprint.py#L21)。类型：`FunctionDef`。

```python
build_manifest(root: Path, *, model_id: str, revision: str) -> dict
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/teacher_model_fingerprint.py 第 68 行](../../../challenge/dataset/teacher_model_fingerprint.py#L68)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `build_manifest` 调用：`ValueError`, `files.append`, `hashlib.sha256`, `hashlib.sha256(canonical).hexdigest`, `json.dumps`, `json.dumps(files, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode`, `len`, `p.is_file`, `p.relative_to`, `p.stat`, `rel.as_posix`, `root.expanduser`, `root.expanduser().resolve`, `root.is_dir`, `root.rglob`, `sha256_file`, `sorted`, `str`.
- `main` 调用：`Path`, `Path(args.model_dir).expanduser`, `Path(args.model_dir).expanduser().resolve`, `SystemExit`, `argparse.ArgumentParser`, `build_manifest`, `json.dumps`, `out.parent.mkdir`, `out.write_text`, `parser.add_argument`, `parser.parse_args`, `print`, `str`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `build_manifest`，第 24 行：`ValueError(f'MODEL_DIR_NOT_FOUND={root}')`。
- `main`，第 83 行：`SystemExit(str(error))`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 70 行：`parser.add_argument('--model-dir', required=True)`。
- 第 71 行：`parser.add_argument('--model-id', default='Qwen/Qwen3.5-2B')`。
- 第 72 行：`parser.add_argument('--revision', required=True)`。
- 第 73 行：`parser.add_argument('--output', default='artifacts/b1_teacher_pinned/teacher_model_manifest.json')`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [challenge/distillation/tests/test_b1_d1_interface.py](../../../challenge/distillation/tests/test_b1_d1_interface.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-data.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/dataset/teacher_model_fingerprint.py`

来源 SHA256：`6d91e00b18f13ac7771d4df074e2f9fa43c8a3f4560a1bcbf1df21c83bc0c9cf`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 70 | `'--model-dir'` | `required=True` |
| 71 | `'--model-id'` | `default='Qwen/Qwen3.5-2B'` |
| 72 | `'--revision'` | `required=True` |
| 73 | `'--output'` | `default='artifacts/b1_teacher_pinned/teacher_model_manifest.json'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `build_manifest` / 24 | `not root.is_dir()` | `raise ValueError(f'MODEL_DIR_NOT_FOUND={root}')` |
| `main` / 83 | `except ValueError` | `raise SystemExit(str(error)) from error` |
