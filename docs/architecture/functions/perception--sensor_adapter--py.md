# sensor_adapter：功能记录

上级模块：[模块说明](../modules/vehicle-perception.md) · 实现：[perception/sensor_adapter.py](../../../perception/sensor_adapter.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [同帧感知、目标身份与来源](perception-authority.md)

## 功能职责与范围

Timestamp, frame, coordinate and bounded-buffer normalization for C.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `Extrinsics.translation_m: tuple[float, float, float]`；默认：`(0.0, 0.0, 0.0)`。
- `Extrinsics.roll_deg: float`；默认：`0.0`。
- `Extrinsics.pitch_deg: float`；默认：`0.0`。
- `Extrinsics.yaw_deg: float`；默认：`0.0`。
- `SensorSample.modality: Modality`；默认：`未在声明处设置`。
- `SensorSample.frame_id: int`；默认：`未在声明处设置`。
- `SensorSample.sim_time_s: float`；默认：`未在声明处设置`。
- `SensorSample.captured_at_ns: int`；默认：`未在声明处设置`。
- `SensorSample.payload: Any`；默认：`未在声明处设置`。
- `SensorSample.extrinsics: Extrinsics`；默认：`Extrinsics()`。
- `SensorSample.valid: bool`；默认：`True`。
- `SensorSample.error_code: str | None`；默认：`None`。
- `AlignedSensorFrame.reference_frame_id: int`；默认：`未在声明处设置`。
- `AlignedSensorFrame.reference_sim_time_s: float`；默认：`未在声明处设置`。
- `AlignedSensorFrame.reference_captured_at_ns: int`；默认：`未在声明处设置`。
- `AlignedSensorFrame.samples: Mapping[Modality, SensorSample]`；默认：`未在声明处设置`。
- `AlignedSensorFrame.modality_valid: Mapping[Modality, bool]`；默认：`未在声明处设置`。
- `AlignedSensorFrame.max_skew_ms: float`；默认：`未在声明处设置`。
- `AlignedSensorFrame.within_tolerance: bool`；默认：`未在声明处设置`。
- `AlignedSensorFrame.stale: bool`；默认：`未在声明处设置`。
- `AlignedSensorFrame.missing_modalities: tuple[Modality, ...]`；默认：`未在声明处设置`。
- `AlignedSensorFrame.degraded_reason_codes: tuple[str, ...]`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `Modality`

源码位置：[perception/sensor_adapter.py 第 16 行](../../../perception/sensor_adapter.py#L16)。类型：`ClassDef`。

固定四种同步模态：RGB、RADAR、LIDAR、VEHICLE_STATE。默认 synchronizer 要求四种齐全；生产 CARLA bridge 的 Radar 可选策略属于另一实现，不能混用默认含义。

### `_finite`

源码位置：[perception/sensor_adapter.py 第 23 行](../../../perception/sensor_adapter.py#L23)。类型：`FunctionDef`。

```python
_finite(name: str, value: object) -> float
```

只接受非布尔 `int/float` 并转为有限 float；类型错误抛 TypeError，NaN/无穷抛 ValueError。正负范围由各调用者另行限制。

### `Extrinsics`

源码位置：[perception/sensor_adapter.py 第 33 行](../../../perception/sensor_adapter.py#L33)。类型：`ClassDef`。

Rigid transform from one sensor frame to ego x-front/y-left/z-up.

### `Extrinsics.__post_init__`

源码位置：[perception/sensor_adapter.py 第 41 行](../../../perception/sensor_adapter.py#L41)。类型：`FunctionDef`。

```python
Extrinsics.__post_init__(self) -> None
```

平移必须是长度3 tuple，各分量与 roll/pitch/yaw 均须有限，成功后全部标准化为 float。角度单位为度，不限制到某个周期。

### `Extrinsics.transform_point`

源码位置：[perception/sensor_adapter.py 第 51 行](../../../perception/sensor_adapter.py#L51)。类型：`FunctionDef`。

```python
Extrinsics.transform_point(self, point_xyz_m: Iterable[float]) -> tuple[float, float, float]
```

对三维点应用 `Rz(yaw) @ Ry(pitch) @ Rx(roll)` 后再加米制平移，输出 ego 前x/左y/上z tuple；输入不是恰好三项或包含非有限值会拒绝。

### `Extrinsics.rotate_vector`

源码位置：[perception/sensor_adapter.py 第 69 行](../../../perception/sensor_adapter.py#L69)。类型：`FunctionDef`。

```python
Extrinsics.rotate_vector(self, vector_xyz: Iterable[float]) -> tuple[float, float, float]
```

分别变换原点和向量端点再相减，从而只保留旋转、消除平移；继承 `transform_point` 的长度和有限值校验。

### `Extrinsics.to_dict`

源码位置：[perception/sensor_adapter.py 第 74 行](../../../perception/sensor_adapter.py#L74)。类型：`FunctionDef`。

```python
Extrinsics.to_dict(self) -> dict[str, Any]
```

输出 JSON 友好的平移 list 与三个度制角度，不附坐标系名称；调用方必须由合同确认这是 sensor→ego 变换。

### `SensorSample`

源码位置：[perception/sensor_adapter.py 第 84 行](../../../perception/sensor_adapter.py#L84)。类型：`ClassDef`。

单模态样本合同：同时携带 CARLA frame、仿真秒、捕获单调纳秒、任意 payload、外参和显式有效性。无效样本仍保留身份/时间，但必须有错误码。

### `SensorSample.__post_init__`

源码位置：[perception/sensor_adapter.py 第 94 行](../../../perception/sensor_adapter.py#L94)。类型：`FunctionDef`。

```python
SensorSample.__post_init__(self) -> None
```

模态和外参必须为对应类型，帧号/捕获纳秒为非负整数，仿真时间为非负有限数，valid 必须 bool；`valid=False` 强制非空错误码。有效样本允许 error_code 非空，用于“有噪但仍可用”等显式标记。

### `SensorSample.invalidated`

源码位置：[perception/sensor_adapter.py 第 112 行](../../../perception/sensor_adapter.py#L112)。类型：`FunctionDef`。

```python
SensorSample.invalidated(self, error_code: str, *, payload: Any=None) -> 'SensorSample'
```

用 dataclass `replace` 保留模态、帧、时间和外参，只替换 payload、`valid=False` 与错误码；新对象会再次经过 post-init，因此空错误码会被拒绝。

### `AlignedSensorFrame`

源码位置：[perception/sensor_adapter.py 第 117 行](../../../perception/sensor_adapter.py#L117)。类型：`ClassDef`。

同步器的不可变结果快照，包含实际选择样本、逐模态有效性、最大捕获偏差、是否齐全/容差内、是否 stale、缺失模态和去重后的降级原因。本 dataclass 自身不复核这些字段间一致性。

### `AlignedSensorFrame.sample`

源码位置：[perception/sensor_adapter.py 第 129 行](../../../perception/sensor_adapter.py#L129)。类型：`FunctionDef`。

```python
AlignedSensorFrame.sample(self, modality: Modality) -> SensorSample | None
```

按模态从 `samples` 映射取值，缺失返回 None；不会检查 `modality_valid`，调用者必须同时读取有效性或整体 stale 状态。

### `SensorSynchronizer`

源码位置：[perception/sensor_adapter.py 第 133 行](../../../perception/sensor_adapter.py#L133)。类型：`ClassDef`。

Align exact CARLA frames without blocking and without false validity.

### `SensorSynchronizer.__init__`

源码位置：[perception/sensor_adapter.py 第 136 行](../../../perception/sensor_adapter.py#L136)。类型：`FunctionDef`。

```python
SensorSynchronizer.__init__(self, *, required_modalities: tuple[Modality, ...]=tuple(Modality), tolerance_ms: float=50.0, max_age_ms: float=150.0, buffer_size: int=8, require_same_frame: bool=True) -> None
```

要求模态 tuple 非空、唯一且都是枚举；容差非负、最大年龄为正、buffer为正整数。为每个必需模态创建线程锁保护的定长 deque；`require_same_frame` 用 `bool()` 转换，非布尔真值也会被接受。

### `SensorSynchronizer.push`

源码位置：[perception/sensor_adapter.py 第 160 行](../../../perception/sensor_adapter.py#L160)。类型：`FunctionDef`。

```python
SensorSynchronizer.push(self, sample: SensorSample) -> None
```

只接收已配置模态的 `SensorSample`。同模态同 frame 的新样本确定性替换旧样本，随后按 `(frame_id,captured_at_ns)` 排序并仅保留 deque 上限的最新项；方法不阻塞等待其他模态。

### `SensorSynchronizer.align`

源码位置：[perception/sensor_adapter.py 第 174 行](../../../perception/sensor_adapter.py#L174)。类型：`FunctionDef`。

```python
SensorSynchronizer.align(self, *, reference_frame_id: int, reference_sim_time_s: float, reference_captured_at_ns: int, now_ns: int) -> AlignedSensorFrame
```

复制锁内缓冲快照后逐模态选样本：同帧模式先过滤 reference frame，再按捕获时间偏差/帧差选最近项。有效性同时要求样本有效且偏差不超阈值；缺失、样本错误、超容差和过期分别写原因。`within_tolerance` 要求无缺失且所有模态有效，`stale` 在超龄或整体不满足时为 true；函数不消费缓冲样本。

### `SensorRecorder`

源码位置：[perception/sensor_adapter.py 第 244 行](../../../perception/sensor_adapter.py#L244)。类型：`ClassDef`。

Append strict JSON samples for deterministic replay.

### `SensorRecorder.__init__`

源码位置：[perception/sensor_adapter.py 第 247 行](../../../perception/sensor_adapter.py#L247)。类型：`FunctionDef`。

```python
SensorRecorder.__init__(self, path: str | Path) -> None
```

创建父目录并以文本独占模式 `x` 打开目标，防止覆盖既有证据；路径已存在会抛 FileExistsError。文件固定 UTF-8 和 LF。

### `SensorRecorder.record`

源码位置：[perception/sensor_adapter.py 第 252 行](../../../perception/sensor_adapter.py#L252)。类型：`FunctionDef`。

```python
SensorRecorder.record(self, sample: SensorSample) -> None
```

要求 `SensorSample`。NumPy payload 转成带 array/dtype/shape 的 JSON 对象，其他 payload 直接交给严格 `json.dumps(allow_nan=False)`；逐行写 schema、时间、外参、有效性并立即 flush。不可序列化或非有限数据会失败，不吞异常。

### `SensorRecorder.close`

源码位置：[perception/sensor_adapter.py 第 276 行](../../../perception/sensor_adapter.py#L276)。类型：`FunctionDef`。

```python
SensorRecorder.close(self) -> None
```

仅在句柄尚未关闭时关闭，重复调用安全；不额外写索引、hash或完成标记。

### `SensorRecorder.__enter__`

源码位置：[perception/sensor_adapter.py 第 280 行](../../../perception/sensor_adapter.py#L280)。类型：`FunctionDef`。

```python
SensorRecorder.__enter__(self) -> 'SensorRecorder'
```

返回 recorder 本身供 `with` 使用，不延迟打开文件；文件已在构造阶段创建。

### `SensorRecorder.__exit__`

源码位置：[perception/sensor_adapter.py 第 283 行](../../../perception/sensor_adapter.py#L283)。类型：`FunctionDef`。

```python
SensorRecorder.__exit__(self, *_: object) -> None
```

无论 with 块是否异常都调用 `close()`，但不返回 true，因此不会抑制原异常。

### `SensorReplayer`

源码位置：[perception/sensor_adapter.py 第 287 行](../../../perception/sensor_adapter.py#L287)。类型：`ClassDef`。

惰性 JSONL replay 入口；只保存路径，真正读文件和构造样本发生在迭代阶段。它验证字段能否构成当前合同，但不验证跨行帧单调、模态齐全或文件 manifest。

### `SensorReplayer.__init__`

源码位置：[perception/sensor_adapter.py 第 288 行](../../../perception/sensor_adapter.py#L288)。类型：`FunctionDef`。

```python
SensorReplayer.__init__(self, path: str | Path) -> None
```

把输入转成 `Path`，不在构造时检查存在性、hash或 schema 版本。

### `SensorReplayer.__iter__`

源码位置：[perception/sensor_adapter.py 第 291 行](../../../perception/sensor_adapter.py#L291)。类型：`FunctionDef`。

```python
SensorReplayer.__iter__(self) -> 未声明返回类型
```

一次性读取 UTF-8 文本并逐行解析；识别 recorder 的精确 array/dtype/shape 三键 payload 并恢复 ndarray，然后重建外参和 `SensorSample`。任意 JSON、字段、枚举、reshape或合同错误统一包装为带1基行号的 ValueError；当前不核对记录中的 `schema_version` 值。

## 内部调用与异常路径

- `_finite` 调用：`TypeError`, `ValueError`, `float`, `isinstance`, `math.isfinite`, `type`.
- `__post_init__` 调用：`TypeError`, `ValueError`, `_finite`, `enumerate`, `getattr`, `isinstance`, `len`, `object.__setattr__`, `tuple`, `type`.
- `transform_point` 调用：`ValueError`, `_finite`, `len`, `math.cos`, `math.radians`, `math.sin`, `tuple`.
- `rotate_vector` 调用：`range`, `self.transform_point`, `tuple`.
- `to_dict` 调用：`list`.
- `invalidated` 调用：`replace`.
- `sample` 调用：`self.samples.get`.
- `__init__` 调用：`Lock`, `Path`, `TypeError`, `ValueError`, `_finite`, `any`, `bool`, `deque`, `isinstance`, `len`, `self.path.open`, `self.path.parent.mkdir`, `set`, `tuple`, `type`.
- `push` 调用：`TypeError`, `ValueError`, `buffer.clear`, `buffer.extend`, `isinstance`, `retained.append`, `retained.sort`.
- `align` 调用：`AlignedSensorFrame`, `ValueError`, `_finite`, `abs`, `all`, `dict.fromkeys`, `max`, `min`, `missing.append`, `reasons.append`, `self._buffers.items`, `skews.append`, `tuple`, `type`, `validity.values`.
- `record` 调用：`TypeError`, `isinstance`, `json.dumps`, `list`, `payload.tolist`, `sample.extrinsics.to_dict`, `self._handle.flush`, `self._handle.write`, `str`.
- `close` 调用：`self._handle.close`.
- `__exit__` 调用：`self.close`.
- `__iter__` 调用：`Extrinsics`, `Modality`, `SensorSample`, `ValueError`, `enumerate`, `isinstance`, `json.loads`, `np.asarray`, `np.asarray(payload['array'], dtype=payload['dtype']).reshape`, `self.path.read_text`, `self.path.read_text(encoding='utf-8').splitlines`, `set`, `tuple`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 146 行：`ValueError('required_modalities must be non-empty and unique')`。
- `__init__`，第 148 行：`TypeError('required_modalities entries must be Modality')`。
- `__init__`，第 152 行：`ValueError('tolerance_ms must be non-negative and max_age_ms positive')`。
- `__init__`，第 154 行：`ValueError('buffer_size must be a positive integer')`。
- `__iter__`，第 311 行：`ValueError(f'invalid sensor replay line {line_number}: {error}')`。
- `__post_init__`，第 43 行：`TypeError('translation_m must be a three-number tuple')`。
- `__post_init__`，第 96 行：`TypeError('modality must be Modality')`。
- `__post_init__`，第 98 行：`ValueError('frame_id must be a non-negative integer')`。
- `__post_init__`，第 101 行：`ValueError('sim_time_s must be non-negative')`。
- `__post_init__`，第 103 行：`ValueError('captured_at_ns must be a non-negative integer')`。
- `__post_init__`，第 105 行：`TypeError('extrinsics must be Extrinsics')`。
- `__post_init__`，第 107 行：`TypeError('valid must be bool')`。
- `__post_init__`，第 109 行：`ValueError('invalid samples require a non-empty error_code')`。
- `_finite`，第 25 行：`TypeError(f'{name} must be numeric')`。
- `_finite`，第 28 行：`ValueError(f'{name} must be finite')`。
- `align`，第 183 行：`ValueError('reference_frame_id must be non-negative')`。
- `align`，第 187 行：`ValueError(f'{name} must be a non-negative integer')`。
- `push`，第 162 行：`TypeError('sample must be SensorSample')`。
- `push`，第 164 行：`ValueError(f'unconfigured modality: {sample.modality.value}')`。
- `record`，第 254 行：`TypeError('sample must be SensorSample')`。
- `transform_point`，第 54 行：`ValueError('point_xyz_m must contain exactly three coordinates')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [perception/__init__.py](../../../perception/__init__.py)
- [perception/fault_injection.py](../../../perception/fault_injection.py)
- [perception/fusion_tracker.py](../../../perception/fusion_tracker.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-perception.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `perception/sensor_adapter.py`

来源 SHA256：`8ae061ecdc6a99ff154e7b28dce410cb1fd4a5721072afd6f1e7749ac442c43a`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `Extrinsics.translation_m` | `tuple[float, float, float]` | `(0.0, 0.0, 0.0)` |
| `Extrinsics.roll_deg` | `float` | `0.0` |
| `Extrinsics.pitch_deg` | `float` | `0.0` |
| `Extrinsics.yaw_deg` | `float` | `0.0` |
| `SensorSample.modality` | `Modality` | `无声明默认；构造/赋值方提供` |
| `SensorSample.frame_id` | `int` | `无声明默认；构造/赋值方提供` |
| `SensorSample.sim_time_s` | `float` | `无声明默认；构造/赋值方提供` |
| `SensorSample.captured_at_ns` | `int` | `无声明默认；构造/赋值方提供` |
| `SensorSample.payload` | `Any` | `无声明默认；构造/赋值方提供` |
| `SensorSample.extrinsics` | `Extrinsics` | `Extrinsics()` |
| `SensorSample.valid` | `bool` | `True` |
| `SensorSample.error_code` | `str &#124; None` | `None` |
| `AlignedSensorFrame.reference_frame_id` | `int` | `无声明默认；构造/赋值方提供` |
| `AlignedSensorFrame.reference_sim_time_s` | `float` | `无声明默认；构造/赋值方提供` |
| `AlignedSensorFrame.reference_captured_at_ns` | `int` | `无声明默认；构造/赋值方提供` |
| `AlignedSensorFrame.samples` | `Mapping[Modality, SensorSample]` | `无声明默认；构造/赋值方提供` |
| `AlignedSensorFrame.modality_valid` | `Mapping[Modality, bool]` | `无声明默认；构造/赋值方提供` |
| `AlignedSensorFrame.max_skew_ms` | `float` | `无声明默认；构造/赋值方提供` |
| `AlignedSensorFrame.within_tolerance` | `bool` | `无声明默认；构造/赋值方提供` |
| `AlignedSensorFrame.stale` | `bool` | `无声明默认；构造/赋值方提供` |
| `AlignedSensorFrame.missing_modalities` | `tuple[Modality, ...]` | `无声明默认；构造/赋值方提供` |
| `AlignedSensorFrame.degraded_reason_codes` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_finite` / 25 | `type(value) not in (int, float) or isinstance(value, bool)` | `raise TypeError(f'{name} must be numeric')` |
| `_finite` / 28 | `not math.isfinite(result)` | `raise ValueError(f'{name} must be finite')` |
| `Extrinsics.__post_init__` / 43 | `type(self.translation_m) is not tuple or len(self.translation_m) != 3` | `raise TypeError('translation_m must be a three-number tuple')` |
| `Extrinsics.transform_point` / 54 | `len(point) != 3` | `raise ValueError('point_xyz_m must contain exactly three coordinates')` |
| `SensorSample.__post_init__` / 96 | `not isinstance(self.modality, Modality)` | `raise TypeError('modality must be Modality')` |
| `SensorSample.__post_init__` / 98 | `type(self.frame_id) is not int or self.frame_id < 0` | `raise ValueError('frame_id must be a non-negative integer')` |
| `SensorSample.__post_init__` / 101 | `sim_time < 0` | `raise ValueError('sim_time_s must be non-negative')` |
| `SensorSample.__post_init__` / 103 | `type(self.captured_at_ns) is not int or self.captured_at_ns < 0` | `raise ValueError('captured_at_ns must be a non-negative integer')` |
| `SensorSample.__post_init__` / 105 | `not isinstance(self.extrinsics, Extrinsics)` | `raise TypeError('extrinsics must be Extrinsics')` |
| `SensorSample.__post_init__` / 107 | `type(self.valid) is not bool` | `raise TypeError('valid must be bool')` |
| `SensorSample.__post_init__` / 109 | `not self.valid and (type(self.error_code) is not str or not self.error_code)` | `raise ValueError('invalid samples require a non-empty error_code')` |
| `SensorSynchronizer.__init__` / 146 | `not required_modalities or len(set(required_modalities)) != len(required_modalities)` | `raise ValueError('required_modalities must be non-empty and unique')` |
| `SensorSynchronizer.__init__` / 148 | `any((not isinstance(item, Modality) for item in required_modalities))` | `raise TypeError('required_modalities entries must be Modality')` |
| `SensorSynchronizer.__init__` / 152 | `self.tolerance_ms < 0 or self.max_age_ms <= 0` | `raise ValueError('tolerance_ms must be non-negative and max_age_ms positive')` |
| `SensorSynchronizer.__init__` / 154 | `type(buffer_size) is not int or buffer_size < 1` | `raise ValueError('buffer_size must be a positive integer')` |
| `SensorSynchronizer.push` / 162 | `not isinstance(sample, SensorSample)` | `raise TypeError('sample must be SensorSample')` |
| `SensorSynchronizer.push` / 164 | `sample.modality not in self._buffers` | `raise ValueError(f'unconfigured modality: {sample.modality.value}')` |
| `SensorSynchronizer.align` / 183 | `type(reference_frame_id) is not int or reference_frame_id < 0` | `raise ValueError('reference_frame_id must be non-negative')` |
| `SensorSynchronizer.align` / 187 | `type(value) is not int or value < 0` | `raise ValueError(f'{name} must be a non-negative integer')` |
| `SensorRecorder.record` / 254 | `not isinstance(sample, SensorSample)` | `raise TypeError('sample must be SensorSample')` |
| `SensorReplayer.__iter__` / 311 | `except Exception` | `raise ValueError(f'invalid sensor replay line {line_number}: {error}') from error` |

### perception/sensor_adapter.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 99 | `_finite('sim_time_s', self.sim_time_s)` |
| 149 | `_finite('tolerance_ms', tolerance_ms)` |
| 150 | `_finite('max_age_ms', max_age_ms)` |
| 184 | `_finite('reference_sim_time_s', reference_sim_time_s)` |
| 55 | `_finite('point', value)` |
| 49 | `_finite(name, getattr(self, name))` |
| 45 | `_finite(f'translation_m[{index}]', value)` |
