# export_group1_sensevoice_onnx_static：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/export_group1_sensevoice_onnx_static.py](../../../tools/export_group1_sensevoice_onnx_static.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Export a fixed-shape SenseVoice ONNX for TensorRT benchmarking.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `StaticSenseVoiceExport`

源码位置：[tools/export_group1_sensevoice_onnx_static.py 第 19 行](../../../tools/export_group1_sensevoice_onnx_static.py#L19)。类型：`ClassDef`。

Hard-code benchmark-time control inputs for a TRT-friendlier graph.

### `StaticSenseVoiceExport.__init__`

源码位置：[tools/export_group1_sensevoice_onnx_static.py 第 22 行](../../../tools/export_group1_sensevoice_onnx_static.py#L22)。类型：`FunctionDef`。

```python
StaticSenseVoiceExport.__init__(self, export_model: nn.Module, frames: int, language_id: int, textnorm_id: int) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StaticSenseVoiceExport.forward`

源码位置：[tools/export_group1_sensevoice_onnx_static.py 第 50 行](../../../tools/export_group1_sensevoice_onnx_static.py#L50)。类型：`FunctionDef`。

```python
StaticSenseVoiceExport.forward(self, speech: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_parse_args`

源码位置：[tools/export_group1_sensevoice_onnx_static.py 第 60 行](../../../tools/export_group1_sensevoice_onnx_static.py#L60)。类型：`FunctionDef`。

```python
_parse_args() -> argparse.Namespace
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/export_group1_sensevoice_onnx_static.py 第 73 行](../../../tools/export_group1_sensevoice_onnx_static.py#L73)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_parse_args` 调用：`argparse.ArgumentParser`, `parser.add_argument`, `parser.parse_args`.
- `main` 调用：`AutoModel`, `FileNotFoundError`, `PeftModel.from_pretrained`, `StaticSenseVoiceExport`, `StaticSenseVoiceExport(export_model=export_model, frames=args.frames, language_id=args.language_id, textnorm_id=args.textnorm_id).to`, `_parse_args`, `args.lora_dir.is_dir`, `args.model.is_dir`, `args.output_dir.mkdir`, `auto_model.model.export`, `export_model.eval`, `export_model.to`, `peft_model.merge_and_unload`, `peft_model.merge_and_unload().to`, `print`, `static_model.eval`, `str`, `torch.no_grad`, `torch.onnx.export`, `torch.randn`.
- `__init__` 调用：`next`, `self.embed`, `self.embed(torch.tensor([[1, 2]], dtype=torch.int32, device=device)).detach`, `self.embed(torch.tensor([language_id], dtype=torch.int32, device=device)).unsqueeze`, `self.embed(torch.tensor([language_id], dtype=torch.int32, device=device)).unsqueeze(1).detach`, `self.embed(torch.tensor([textnorm_id], dtype=torch.int32, device=device)).unsqueeze`, `self.embed(torch.tensor([textnorm_id], dtype=torch.int32, device=device)).unsqueeze(1).detach`, `self.embed.parameters`, `self.register_buffer`, `super`, `super().__init__`, `torch.tensor`.
- `forward` 调用：`isinstance`, `self.ctc.ctc_lo`, `self.encoder`, `torch.cat`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 76 行：`FileNotFoundError(f'Model directory not found: {args.model}')`。
- `main`，第 82 行：`FileNotFoundError(f'LoRA directory not found: {args.lora_dir}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 62 行：`parser.add_argument('--model', type=Path, default=DEFAULT_MODEL)`。
- 第 63 行：`parser.add_argument('--lora-dir', type=Path)`。
- 第 64 行：`parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT)`。
- 第 65 行：`parser.add_argument('--device', default='cuda')`。
- 第 66 行：`parser.add_argument('--frames', type=int, default=51)`。
- 第 67 行：`parser.add_argument('--opset-version', type=int, default=18)`。
- 第 68 行：`parser.add_argument('--language-id', type=int, default=0)`。
- 第 69 行：`parser.add_argument('--textnorm-id', type=int, default=14)`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/export_group1_sensevoice_onnx_static.py`

来源 SHA256：`01a7717de528e7a77d07861e21089f13564833bb26217e1ac448d42b2483b8e0`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 62 | `'--model'` | `type=Path; default=DEFAULT_MODEL` |
| 63 | `'--lora-dir'` | `type=Path` |
| 64 | `'--output-dir'` | `type=Path; default=DEFAULT_OUTPUT` |
| 65 | `'--device'` | `default='cuda'` |
| 66 | `'--frames'` | `type=int; default=51` |
| 67 | `'--opset-version'` | `type=int; default=18` |
| 68 | `'--language-id'` | `type=int; default=0` |
| 69 | `'--textnorm-id'` | `type=int; default=14` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `main` / 76 | `not args.model.is_dir()` | `raise FileNotFoundError(f'Model directory not found: {args.model}')` |
| `main` / 82 | `args.lora_dir is not None AND not args.lora_dir.is_dir()` | `raise FileNotFoundError(f'LoRA directory not found: {args.lora_dir}')` |
