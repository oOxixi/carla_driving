# run_generalization_gate：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/run_generalization_gate.py](../../../tools/run_generalization_gate.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Build and validate deterministic in-memory scenario perturbations.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_scenario_paths`

源码位置：[tools/run_generalization_gate.py 第 24 行](../../../tools/run_generalization_gate.py#L24)。类型：`FunctionDef`。

```python
_scenario_paths(values: list[str], holdout: bool, matrix: GeneralizationMatrix) -> tuple[Path, ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/run_generalization_gate.py 第 34 行](../../../tools/run_generalization_gate.py#L34)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_scenario_paths` 调用：`(ROOT / 'scenarios' / 'official_competition').glob`, `(ROOT / item).resolve`, `Path`, `Path(item).expanduser`, `Path(item).expanduser().resolve`, `sorted`, `tuple`.
- `main` 调用：`Path`, `Path(args.output_dir).expanduser`, `Path(args.output_dir).expanduser().resolve`, `ScenarioSpec.load`, `_scenario_paths`, `argparse.ArgumentParser`, `failures.append`, `json.dumps`, `json.loads`, `len`, `load_generalization_matrix`, `matrix.cases`, `nullcontext`, `output_root.mkdir`, `parser.add_argument`, `parser.error`, `parser.parse_args`, `perturb_scenario`, `print`, `raw.get`, `source.read_text`, `str`, `target.write_text`, `tempfile.TemporaryDirectory`, `type`, `variant.get`, `variant.get('extensions', {}).get`, `variant.get('extensions', {}).get('generalization_case', {}).get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 36 行：`parser.add_argument('scenario', nargs='*', help='base scenario JSON; defaults to official competition scenarios')`。
- 第 37 行：`parser.add_argument('--matrix', help='generalization matrix JSON')`。
- 第 38 行：`parser.add_argument('--holdout', action='store_true', help='validate only the frozen holdout set')`。
- 第 39 行：`parser.add_argument('--kind', choices=('all', 'variant', 'unseen'), default='all', help='keep same-map variants, cross-map unseen cases, or both')`。
- 第 43 行：`parser.add_argument('--output-dir', help='write concrete reproducible scenario JSON files instead of temporary files')`。
- 第 47 行：`parser.add_argument('--max-per-scenario', type=int, help='bound emitted cases per base scenario after --kind filtering')`。

## 上下游与关联验证

静态导入的项目内实现：

- [integration/generalization_gate.py](../../../integration/generalization_gate.py)
- [integration/scenario_execution.py](../../../integration/scenario_execution.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/run_generalization_gate.py`

来源 SHA256：`5165cffa84abb7938a42f8f3ed51a38e3377580c8c3f4ac3214b6cec211fbb2d`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 36 | `'scenario'` | `nargs='*'; help='base scenario JSON; defaults to official competition scenarios'` |
| 37 | `'--matrix'` | `help='generalization matrix JSON'` |
| 38 | `'--holdout'` | `action='store_true'; help='validate only the frozen holdout set'` |
| 39 | `'--kind'` | `choices=('all', 'variant', 'unseen'); default='all'; help='keep same-map variants, cross-map unseen cases, or both'` |
| 43 | `'--output-dir'` | `help='write concrete reproducible scenario JSON files instead of temporary files'` |
| 47 | `'--max-per-scenario'` | `type=int; help='bound emitted cases per base scenario after --kind filtering'` |
