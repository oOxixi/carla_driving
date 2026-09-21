# perception_stage：功能记录

上级模块：[模块说明](../modules/vehicle-perception.md) · 实现：[integration/perception_stage.py](../../../integration/perception_stage.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [同帧感知、目标身份与来源](perception-authority.md)

## 功能职责与范围

Perception/control source boundary for the CARLA runtime.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `PerceptionSourceAudit.authority_by_field: Mapping[str, str]`；默认：`未在声明处设置`。
- `PerceptionSourceAudit.forbidden_control_fields: tuple[str, ...]`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `ObservationAuthority`

源码位置：[integration/perception_stage.py 第 15 行](../../../integration/perception_stage.py#L15)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `classify_observation_source`

源码位置：[integration/perception_stage.py 第 35 行](../../../integration/perception_stage.py#L35)。类型：`FunctionDef`。

```python
classify_observation_source(source: str) -> ObservationAuthority
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `PerceptionSourceAudit`

源码位置：[integration/perception_stage.py 第 51 行](../../../integration/perception_stage.py#L51)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `PerceptionSourceAudit.control_clean`

源码位置：[integration/perception_stage.py 第 56 行](../../../integration/perception_stage.py#L56)。类型：`FunctionDef`。

```python
PerceptionSourceAudit.control_clean(self) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `PerceptionSourceAudit.to_dict`

源码位置：[integration/perception_stage.py 第 59 行](../../../integration/perception_stage.py#L59)。类型：`FunctionDef`。

```python
PerceptionSourceAudit.to_dict(self) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `audit_control_sources`

源码位置：[integration/perception_stage.py 第 67 行](../../../integration/perception_stage.py#L67)。类型：`FunctionDef`。

```python
audit_control_sources(source_by_field: Mapping[str, str], *, strict_sensor_mode: bool) -> PerceptionSourceAudit
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `classify_observation_source` 调用：`any`, `str`, `str(source).strip`, `str(source).strip().upper`.
- `audit_control_sources` 调用：`MappingProxyType`, `PerceptionSourceAudit`, `authorities.items`, `classify_observation_source`, `sorted`, `source_by_field.items`, `str`, `tuple`.
- `to_dict` 调用：`dict`, `list`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/tests/test_perception_stage.py](../../../integration/tests/test_perception_stage.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-perception.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/perception_stage.py`

来源 SHA256：`3832192dc2d594f776e545fd5424481b125bd637a38a76581a2ae88337fd30d4`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `PerceptionSourceAudit.authority_by_field` | `Mapping[str, str]` | `无声明默认；构造/赋值方提供` |
| `PerceptionSourceAudit.forbidden_control_fields` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
