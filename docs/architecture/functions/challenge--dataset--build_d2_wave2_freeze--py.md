# build_d2_wave2_freeze：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/build_d2_wave2_freeze.py](../../../challenge/dataset/build_d2_wave2_freeze.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

build_d2_wave2_freeze

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[challenge/dataset/build_d2_wave2_freeze.py 第 57 行](../../../challenge/dataset/build_d2_wave2_freeze.py#L57)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `read_jsonl`

源码位置：[challenge/dataset/build_d2_wave2_freeze.py 第 65 行](../../../challenge/dataset/build_d2_wave2_freeze.py#L65)。类型：`FunctionDef`。

```python
read_jsonl(path: Path) -> list[dict]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/build_d2_wave2_freeze.py 第 74 行](../../../challenge/dataset/build_d2_wave2_freeze.py#L74)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `read_jsonl` 调用：`json.loads`, `line.strip`, `path.open`, `rows.append`.
- `main` 调用：`(row.get('sample_class') or {}).get`, `Counter`, `Path`, `Path(args.plan).resolve`, `Path(args.root).resolve`, `Path.cwd`, `argparse.ArgumentParser`, `dict`, `freeze_path.write_text`, `group_keys.append`, `hn_reasons.items`, `identity_tuples.append`, `json.dumps`, `json.loads`, `len`, `line.count`, `logs_root.rglob`, `meta.get`, `p.is_absolute`, `p.is_file`, `p.open`, `p.stat`, `parser.add_argument`, `parser.parse_args`, `print`, `prov_path.read_text`, `quality.get`, `read_jsonl`, `row.get`, `runs.values`, `sample_classes.items`, `set`, `sha256_file`, `sorted`, `state_path.read_text`, `str`, `visual.get`, `x.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 76 行：`parser.add_argument('--root', default='artifacts/b1_d2_wave2_2000_teacher_v4')`。
- 第 80 行：`parser.add_argument('--plan', default='artifacts/b1_d2_expansion_plan_wave2_v1/d2_expansion_plan_wave2.json')`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-data.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/dataset/build_d2_wave2_freeze.py`

来源 SHA256：`4ef629c3ea46b7f4b6fef61cfea86c273a00d6f46e30383101f2107f9e1dfd09`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 76 | `'--root'` | `default='artifacts/b1_d2_wave2_2000_teacher_v4'` |
| 80 | `'--plan'` | `default='artifacts/b1_d2_expansion_plan_wave2_v1/d2_expansion_plan_wave2.json'` |
