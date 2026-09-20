# replay_acceptance：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/replay_acceptance.py](../../../tools/replay_acceptance.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Run RGB/LiDAR/Qwen records through the offline A/B/C/D acceptance chain.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `build_parser`

源码位置：[tools/replay_acceptance.py 第 18 行](../../../tools/replay_acceptance.py#L18)。类型：`FunctionDef`。

```python
build_parser() -> argparse.ArgumentParser
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/replay_acceptance.py 第 29 行](../../../tools/replay_acceptance.py#L29)。类型：`FunctionDef`。

```python
main(argv: list[str] | None=None) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `build_parser` 调用：`argparse.ArgumentParser`, `parser.add_argument`.
- `main` 调用：`OnnxYoloDetector`, `build_parser`, `build_parser().parse_args`, `json.dumps`, `list`, `print`, `run_replay_manifest`, `str`, `type`, `write_replay_report`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 20 行：`parser.add_argument('manifest', help='UTF-8 JSONL replay manifest')`。
- 第 21 行：`parser.add_argument('--output', help='optional JSON acceptance report path')`。
- 第 22 行：`parser.add_argument('--rgb-detector-model', help='optional YOLO ONNX model')`。
- 第 23 行：`parser.add_argument('--confidence', type=float, default=0.35)`。
- 第 24 行：`parser.add_argument('--iou', type=float, default=0.45)`。
- 第 25 行：`parser.add_argument('--input-size', type=int, default=640)`。

## 上下游与关联验证

静态导入的项目内实现：

- [integration/offline_replay.py](../../../integration/offline_replay.py)
- [integration/rgb_detector.py](../../../integration/rgb_detector.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/replay_acceptance.py`

来源 SHA256：`e048e2c5fd14551564c1a9564e9352f1459e7ee2f9ba67332ca3f401e83af907`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 20 | `'manifest'` | `help='UTF-8 JSONL replay manifest'` |
| 21 | `'--output'` | `help='optional JSON acceptance report path'` |
| 22 | `'--rgb-detector-model'` | `help='optional YOLO ONNX model'` |
| 23 | `'--confidence'` | `type=float; default=0.35` |
| 24 | `'--iou'` | `type=float; default=0.45` |
| 25 | `'--input-size'` | `type=int; default=640` |
