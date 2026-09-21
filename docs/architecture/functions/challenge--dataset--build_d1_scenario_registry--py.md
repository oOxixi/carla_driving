# build_d1_scenario_registry：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/build_d1_scenario_registry.py](../../../challenge/dataset/build_d1_scenario_registry.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

build_d1_scenario_registry

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `load_json`

源码位置：[challenge/dataset/build_d1_scenario_registry.py 第 40 行](../../../challenge/dataset/build_d1_scenario_registry.py#L40)。类型：`FunctionDef`。

```python
load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `runnable_reason`

源码位置：[challenge/dataset/build_d1_scenario_registry.py 第 50 行](../../../challenge/dataset/build_d1_scenario_registry.py#L50)。类型：`FunctionDef`。

```python
runnable_reason(data: dict[str, Any]) -> str | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `source_bucket`

源码位置：[challenge/dataset/build_d1_scenario_registry.py 第 70 行](../../../challenge/dataset/build_d1_scenario_registry.py#L70)。类型：`FunctionDef`。

```python
source_bucket(rel: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `family`

源码位置：[challenge/dataset/build_d1_scenario_registry.py 第 79 行](../../../challenge/dataset/build_d1_scenario_registry.py#L79)。类型：`FunctionDef`。

```python
family(rel: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `classify`

源码位置：[challenge/dataset/build_d1_scenario_registry.py 第 84 行](../../../challenge/dataset/build_d1_scenario_registry.py#L84)。类型：`FunctionDef`。

```python
classify(rel: str, data: dict[str, Any]) -> tuple[str, str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/build_d1_scenario_registry.py 第 131 行](../../../challenge/dataset/build_d1_scenario_registry.py#L131)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `load_json` 调用：`isinstance`, `json.loads`, `path.read_text`, `type`.
- `runnable_reason` 调用：`data.get`, `isinstance`, `level.strip`, `sid.strip`.
- `source_bucket` 调用：`rel.lower`.
- `family` 调用：`Path`.
- `classify` 调用：`' '.join`, `' '.join((str(cmd.get(k) or '') for k in ('source_text', 'intent', 'status'))).lower`, `any`, `cmd.get`, `data.get`, `data.get('extensions', {}).get`, `family`, `family(rel).lower`, `isinstance`, `rel.lower`, `runnable_reason`, `str`, `str(cmd.get('status') or '').lower`.
- `main` 调用：`Counter`, `Path`, `Path(args.output_dir).resolve`, `Path(args.scenarios_root).resolve`, `argparse.ArgumentParser`, `classify`, `csv.DictWriter`, `csv_path.open`, `data.get`, `dict`, `family`, `int`, `isinstance`, `json.dumps`, `json_path.write_text`, `len`, `load_json`, `out_dir.mkdir`, `parser.add_argument`, `parser.parse_args`, `path.relative_to`, `path.relative_to(root).as_posix`, `policy_counts.get`, `policy_counts.items`, `print`, `root.rglob`, `rows.append`, `sorted`, `source_bucket`, `source_counts.items`, `str`, `sum`, `summary_path.write_text`, `w.writeheader`, `w.writerows`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 133 行：`parser.add_argument('--scenarios-root', default='scenarios')`。
- 第 134 行：`parser.add_argument('--output-dir', default='artifacts/b1_d1_registry_v3')`。

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

### `challenge/dataset/build_d1_scenario_registry.py`

来源 SHA256：`c8cf0e25b85825e4147ba5ae5d60a6429c9d0d9383674e5f6b690af4a1a96bde`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 133 | `'--scenarios-root'` | `default='scenarios'` |
| 134 | `'--output-dir'` | `default='artifacts/b1_d1_registry_v3'` |
