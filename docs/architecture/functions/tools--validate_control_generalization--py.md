# validate_control_generalization：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/validate_control_generalization.py](../../../tools/validate_control_generalization.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

CARLA-free numerical validation for the member-3 generalization policy.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `main`

源码位置：[tools/validate_control_generalization.py 第 21 行](../../../tools/validate_control_generalization.py#L21)。类型：`FunctionDef`。

```python
main() -> None
```

【main】是维护工具的数据检查、生成、评测或证据处理的执行/命令入口；参数来自紧邻签名或本页CLI表，可能读取外部资源、写产物或启动服务，应以退出码、原始日志和固定输入身份判定结果。

## 内部调用与异常路径

- `main` 调用：`LongitudinalController`, `LongitudinalRequest`, `PurePursuitController`, `PurePursuitController().step`, `RouteReference`, `RuntimeVehicleState`, `SafetySupervisor`, `VehiclePose`, `controller.step`, `curvatures.items`, `dynamic_safety_distance`, `float`, `json.dumps`, `lateral_checks.append`, `len`, `longitudinal_checks.append`, `math.sqrt`, `matrix.append`, `print`, `range`, `round`, `supervisor.arbitrate`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_B/__init__.py](../../../car_control_B/__init__.py)
- [car_control_C/__init__.py](../../../car_control_C/__init__.py)
- [car_control_D/__init__.py](../../../car_control_D/__init__.py)
- [config/strategy.py](../../../config/strategy.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/validate_control_generalization.py`

来源 SHA256：`660e0651f4e571ea431caa8f2c4e4219fc10fb374da65edc09bb66dbf9a633fa`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
