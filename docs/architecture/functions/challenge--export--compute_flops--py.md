# compute_flops：功能记录

上级模块：[模块说明](../modules/challenge-export.md) · 实现：[challenge/export/compute_flops.py](../../../challenge/export/compute_flops.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [随机结构导出、来源SHA与报告](onnx-delivery.md)

## 功能职责与范围

Deterministic Conv/Linear parameter and FLOPs report for Student V0.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `analyze_model`

源码位置：[challenge/export/compute_flops.py 第 18 行](../../../challenge/export/compute_flops.py#L18)。类型：`FunctionDef`。

```python
analyze_model() -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `analyze_model.register`

源码位置：[challenge/export/compute_flops.py 第 25 行](../../../challenge/export/compute_flops.py#L25)。类型：`FunctionDef`。

```python
analyze_model.register(name: str, module: nn.Module) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `analyze_model.register.hook`

源码位置：[challenge/export/compute_flops.py 第 26 行](../../../challenge/export/compute_flops.py#L26)。类型：`FunctionDef`。

```python
analyze_model.register.hook(layer: nn.Module, inputs: tuple[torch.Tensor, ...], output: torch.Tensor) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/export/compute_flops.py 第 93 行](../../../challenge/export/compute_flops.py#L93)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `analyze_model` 调用：`StudentModelConfig`, `StudentPlannerV0`, `StudentPlannerV0(contract, config).eval`, `StudentShapeContract`, `contract.input_shapes.items`, `contract.input_shapes.values`, `handle.remove`, `handles.append`, `int`, `isinstance`, `list`, `macs_by_module.values`, `model`, `model.named_modules`, `model.parameters`, `module.register_forward_hook`, `output.numel`, `parameter.numel`, `register`, `subprocess.check_output`, `subprocess.check_output(('git', 'rev-parse', 'HEAD'), text=True, encoding='utf-8').strip`, `sum`, `torch.inference_mode`, `torch.zeros`, `tuple`.
- `main` 调用：`Path`, `analyze_model`, `argparse.ArgumentParser`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `path.parent.mkdir`, `path.write_text`, `print`.
- `register` 调用：`handles.append`, `int`, `isinstance`, `module.register_forward_hook`, `output.numel`.
- `hook` 调用：`int`, `isinstance`, `output.numel`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 95 行：`parser.add_argument('--output', default='challenge/flops_report.json')`。

## 上下游与关联验证

静态导入的项目内实现：

- [challenge/student/contract.py](../../../challenge/student/contract.py)
- [challenge/student/model.py](../../../challenge/student/model.py)

静态 import 消费者（含测试）：

- [challenge/export/export_onnx.py](../../../challenge/export/export_onnx.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-export.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/export/compute_flops.py`

来源 SHA256：`cdae058df9a1afd47287585b221666fcb7e285bfbf186bb93ca1f6e94bab1f88`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 95 | `'--output'` | `default='challenge/flops_report.json'` |
