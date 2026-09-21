# rgb_pipeline：功能记录

上级模块：[模块说明](../modules/vehicle-longitudinal.md) · 实现：[car_control_C/rgb_pipeline.py](../../../car_control_C/rgb_pipeline.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [目标速度、跟车风险与D交接](longitudinal-safety-contract.md)

## 功能职责与范围

C-role RGB pipeline summary helpers.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `RgbDetection.class_name: str`；默认：`未在声明处设置`。
- `RgbDetection.confidence: float`；默认：`未在声明处设置`。
- `RgbDetection.bbox_xyxy_norm: tuple[float, float, float, float]`；默认：`未在声明处设置`。
- `RgbDetection.source: str`；默认：`未在声明处设置`。
- `RgbDetection.track_id: str | None`；默认：`None`。
- `RgbPipelineSummary.frame_id: int`；默认：`未在声明处设置`。
- `RgbPipelineSummary.top_k: tuple[RgbDetection, ...]`；默认：`未在声明处设置`。
- `RgbPipelineSummary.p95_latency_ms: float | None`；默认：`未在声明处设置`。
- `RgbPipelineSummary.p95_within_30ms: bool | None`；默认：`未在声明处设置`。
- `RgbPipelineSummary.roi_policy: str`；默认：`未在声明处设置`。
- `RgbPipelineSummary.jump_guard: str`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `RgbDetection`

源码位置：[car_control_C/rgb_pipeline.py 第 16 行](../../../car_control_C/rgb_pipeline.py#L16)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `RgbDetection.__post_init__`

源码位置：[car_control_C/rgb_pipeline.py 第 23 行](../../../car_control_C/rgb_pipeline.py#L23)。类型：`FunctionDef`。

```python
RgbDetection.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `RgbDetection.to_dict`

源码位置：[car_control_C/rgb_pipeline.py 第 36 行](../../../car_control_C/rgb_pipeline.py#L36)。类型：`FunctionDef`。

```python
RgbDetection.to_dict(self) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `RgbPipelineSummary`

源码位置：[car_control_C/rgb_pipeline.py 第 47 行](../../../car_control_C/rgb_pipeline.py#L47)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `RgbPipelineSummary.to_dict`

源码位置：[car_control_C/rgb_pipeline.py 第 55 行](../../../car_control_C/rgb_pipeline.py#L55)。类型：`FunctionDef`。

```python
RgbPipelineSummary.to_dict(self) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_nearest_rank_p95`

源码位置：[car_control_C/rgb_pipeline.py 第 67 行](../../../car_control_C/rgb_pipeline.py#L67)。类型：`FunctionDef`。

```python
_nearest_rank_p95(values: Sequence[float]) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `summarize_rgb_pipeline`

源码位置：[car_control_C/rgb_pipeline.py 第 75 行](../../../car_control_C/rgb_pipeline.py#L75)。类型：`FunctionDef`。

```python
summarize_rgb_pipeline(*, frame_id: int, detections: Iterable[RgbDetection], top_k: int=5, latency_ms_samples: Sequence[float]=()) -> RgbPipelineSummary
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_nearest_rank_p95` 调用：`float`, `len`, `math.ceil`, `max`, `sorted`.
- `summarize_rgb_pipeline` 调用：`RgbPipelineSummary`, `ValueError`, `_nearest_rank_p95`, `sorted`, `tuple`.
- `__post_init__` 调用：`ValueError`, `float`, `len`, `self.class_name.strip`, `self.source.strip`.
- `to_dict` 调用：`float`, `item.to_dict`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 25 行：`ValueError('class_name must be non-empty')`。
- `__post_init__`，第 27 行：`ValueError('confidence must be in [0, 1]')`。
- `__post_init__`，第 29 行：`ValueError('bbox_xyxy_norm must contain four values')`。
- `__post_init__`，第 32 行：`ValueError('bbox coordinates must be normalized to [0, 1]')`。
- `__post_init__`，第 34 行：`ValueError('source must be non-empty')`。
- `summarize_rgb_pipeline`，第 83 行：`ValueError('top_k must be positive')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [car_control_C/tests/test_c_deliverables.py](../../../car_control_C/tests/test_c_deliverables.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-longitudinal.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_C/rgb_pipeline.py`

来源 SHA256：`8b4d600b007f5a3aa09d15fe1696e4ebbc0700624433980b8d7caa3f8f99cefe`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `RgbDetection.class_name` | `str` | `无声明默认；构造/赋值方提供` |
| `RgbDetection.confidence` | `float` | `无声明默认；构造/赋值方提供` |
| `RgbDetection.bbox_xyxy_norm` | `tuple[float, float, float, float]` | `无声明默认；构造/赋值方提供` |
| `RgbDetection.source` | `str` | `无声明默认；构造/赋值方提供` |
| `RgbDetection.track_id` | `str &#124; None` | `None` |
| `RgbPipelineSummary.frame_id` | `int` | `无声明默认；构造/赋值方提供` |
| `RgbPipelineSummary.top_k` | `tuple[RgbDetection, ...]` | `无声明默认；构造/赋值方提供` |
| `RgbPipelineSummary.p95_latency_ms` | `float &#124; None` | `无声明默认；构造/赋值方提供` |
| `RgbPipelineSummary.p95_within_30ms` | `bool &#124; None` | `无声明默认；构造/赋值方提供` |
| `RgbPipelineSummary.roi_policy` | `str` | `无声明默认；构造/赋值方提供` |
| `RgbPipelineSummary.jump_guard` | `str` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `RgbDetection.__post_init__` / 25 | `not self.class_name.strip()` | `raise ValueError('class_name must be non-empty')` |
| `RgbDetection.__post_init__` / 27 | `not 0.0 <= float(self.confidence) <= 1.0` | `raise ValueError('confidence must be in [0, 1]')` |
| `RgbDetection.__post_init__` / 29 | `len(self.bbox_xyxy_norm) != 4` | `raise ValueError('bbox_xyxy_norm must contain four values')` |
| `RgbDetection.__post_init__` / 32 | `not 0.0 <= float(value) <= 1.0` | `raise ValueError('bbox coordinates must be normalized to [0, 1]')` |
| `RgbDetection.__post_init__` / 34 | `not self.source.strip()` | `raise ValueError('source must be non-empty')` |
| `summarize_rgb_pipeline` / 83 | `top_k < 1` | `raise ValueError('top_k must be positive')` |
