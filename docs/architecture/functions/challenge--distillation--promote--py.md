# promote：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/promote.py](../../../challenge/distillation/promote.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

CLI for the evidence-gated A3 FP32 weight manifest.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_read`

源码位置：[challenge/distillation/promote.py 第 13 行](../../../challenge/distillation/promote.py#L13)。类型：`FunctionDef`。

```python
_read(path: str | Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/distillation/promote.py 第 20 行](../../../challenge/distillation/promote.py#L20)。类型：`FunctionDef`。

```python
main(argv: Sequence[str] | None=None) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_read` 调用：`Path`, `Path(path).read_text`, `ValueError`, `isinstance`, `json.loads`.
- `main` 调用：`_read`, `argparse.ArgumentParser`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`, `promote_fp32_candidate`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_read`，第 16 行：`ValueError(f'{path}: expected a JSON object')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 22 行：`parser.add_argument('--candidate', required=True)`。
- 第 23 行：`parser.add_argument('--weights', required=True)`。
- 第 24 行：`parser.add_argument('--teacher-evaluation', required=True)`。
- 第 25 行：`parser.add_argument('--student-evaluation', required=True)`。
- 第 26 行：`parser.add_argument('--output', required=True)`。
- 第 27 行：`parser.add_argument('--max-core-drop', type=float, default=0.015)`。
- 第 28 行：`parser.add_argument('--max-safety-drop', type=float, default=0.0)`。

## 上下游与关联验证

静态导入的项目内实现：

- [challenge/distillation/artifacts.py](../../../challenge/distillation/artifacts.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/promote.py`

来源 SHA256：`362e6522308225eec5522254c2ed140e61de71c24cec8e1a28bf72d269c6b91a`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 22 | `'--candidate'` | `required=True` |
| 23 | `'--weights'` | `required=True` |
| 24 | `'--teacher-evaluation'` | `required=True` |
| 25 | `'--student-evaluation'` | `required=True` |
| 26 | `'--output'` | `required=True` |
| 27 | `'--max-core-drop'` | `type=float; default=0.015` |
| 28 | `'--max-safety-drop'` | `type=float; default=0.0` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_read` / 16 | `not isinstance(value, dict)` | `raise ValueError(f'{path}: expected a JSON object')` |
