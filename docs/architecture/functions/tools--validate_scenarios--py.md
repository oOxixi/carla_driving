# validate_scenarios：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/validate_scenarios.py](../../../tools/validate_scenarios.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

validate_scenarios

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `validate_one`

源码位置：[tools/validate_scenarios.py 第 17 行](../../../tools/validate_scenarios.py#L17)。类型：`FunctionDef`。

```python
validate_one(path: Path) -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/validate_scenarios.py 第 110 行](../../../tools/validate_scenarios.py#L110)。类型：`FunctionDef`。

```python
main() -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `validate_one` 调用：`', '.join`, `abs`, `actor.get`, `data.get`, `data.get('category', '').startswith`, `errors.append`, `float`, `isinstance`, `json.loads`, `len`, `math.isfinite`, `path.read_text`, `qwen_expected.get`, `qwen_fault.get`, `route.get`, `route_position.get`, `runtime.get`, `set`, `sorted`, `str`, `str(actor.get('type', 'vehicle')).strip`, `str(actor.get('type', 'vehicle')).strip().lower`, `type`.
- `main` 调用：`Path`, `Path(__file__).resolve`, `SystemExit`, `path.relative_to`, `print`, `root.rglob`, `sorted`, `validate_one`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 130 行：`SystemExit(1)`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_qwen_scenario_contracts.py](../../../integration/tests/test_qwen_scenario_contracts.py)
- [integration/tests/test_validate_scenarios.py](../../../integration/tests/test_validate_scenarios.py)
- [tools/validate_official_scenes.py](../../../tools/validate_official_scenes.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/validate_scenarios.py`

来源 SHA256：`2073703287dc2225365265b3459c2f7359dcc07a450fbb97b9e7f30b37c1f2a7`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `main` / 130 | `failed` | `raise SystemExit(1)` |
