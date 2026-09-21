# lateral_controller_base：功能记录

上级模块：[模块说明](../modules/vehicle-lateral.md) · 实现：[car_control_B/lateral_controller_base.py](../../../car_control_B/lateral_controller_base.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [路线、跟踪控制与完成里程](route-control-progress.md)

## 功能职责与范围

Base interface for lateral controllers.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `LateralController`

源码位置：[car_control_B/lateral_controller_base.py 第 13 行](../../../car_control_B/lateral_controller_base.py#L13)。类型：`ClassDef`。

B-side controller contract.

A should call step(vehicle_state, route_reference) and use only output.steer.
B never calls CARLA apply_control and never modifies throttle/brake.

### `LateralController.reset`

源码位置：[car_control_B/lateral_controller_base.py 第 21 行](../../../car_control_B/lateral_controller_base.py#L21)。类型：`FunctionDef`。

```python
LateralController.reset(self, *, preserve_steer: bool=False) -> None
```

Reset route-progress state, optionally retaining steering continuity.

### `LateralController.step`

源码位置：[car_control_B/lateral_controller_base.py 第 26 行](../../../car_control_B/lateral_controller_base.py#L26)。类型：`FunctionDef`。

```python
LateralController.step(self, vehicle: VehiclePose, reference: RouteReference) -> LateralOutput
```

抽象逐帧接口；具体控制器必须消费已验证的 `VehiclePose` 与 `RouteReference` 并返回 `LateralOutput`。基类不提供降级控制，也不吞掉实现异常。

### `LateralController._adapt_reference_any`

源码位置：[car_control_B/lateral_controller_base.py 第 29 行](../../../car_control_B/lateral_controller_base.py#L29)。类型：`FunctionDef`。

```python
LateralController._adapt_reference_any(self, reference: Any) -> RouteReference
```

按原始点容器的对象身份复用适配后的路线，避免每帧复制；缓存保存源容器本身以规避 Python id 复用，超过 32 项时删除最旧项。未命中时调用 `adapt_route_reference`，因此别名、默认值和异常沿用适配器。

### `LateralController.step_any`

源码位置：[car_control_B/lateral_controller_base.py 第 56 行](../../../car_control_B/lateral_controller_base.py#L56)。类型：`FunctionDef`。

```python
LateralController.step_any(self, vehicle_state: Any, reference: Any) -> LateralOutput
```

先适配并缓存任意形态的路线，再把车辆 Mapping/对象适配为 `VehiclePose`，最后调用具体控制器 `step`；返回完整横向输出，不直接调用 CARLA。

### `LateralController.steer`

源码位置：[car_control_B/lateral_controller_base.py 第 60 行](../../../car_control_B/lateral_controller_base.py#L60)。类型：`FunctionDef`。

```python
LateralController.steer(self, vehicle_state: Any, reference: Any) -> float
```

Compatibility helper for A handoff wording.

## 内部调用与异常路径

- `_adapt_reference_any` 调用：`adapt_route_reference`, `cache.append`, `getattr`, `isinstance`, `len`, `next`, `reference.get`, `setattr`.
- `step_any` 调用：`adapt_vehicle_pose`, `self._adapt_reference_any`, `self.step`.
- `steer` 调用：`self.step_any`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_B/adapters.py](../../../car_control_B/adapters.py)
- [car_control_B/schemas.py](../../../car_control_B/schemas.py)

静态 import 消费者（含测试）：

- [car_control_B/pure_pursuit.py](../../../car_control_B/pure_pursuit.py)
- [car_control_B/stanley.py](../../../car_control_B/stanley.py)
- [integration/runtime_loop.py](../../../integration/runtime_loop.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-lateral.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_B/lateral_controller_base.py`

来源 SHA256：`e642b43a48f0f736b151e2a31bc88ac928a90ab40269ad3b9d6b485f9c91cd66`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
