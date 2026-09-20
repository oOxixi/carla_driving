# 接口版本、数据类型与时间/坐标边界

上级：[接口模块](../modules/vehicle-interfaces.md)。

## 三种接口不能互相代替

JSON Schema 定义跨模块交换字段和允许值；Python dataclass 定义进程内数据对象；Adapter 负责验证、补充上下文、单位及表示转换。结构看起来相似不意味着可以跳过转换直接传递。

交换契约位于 [interfaces](../../../interfaces)，注册/验证由 [InterfaceRegistry](../../../runtime/interface_registry.py) 执行。ModelRequest 使用 1.0，ManeuverPlan 独立使用 2.0；未知字段是否允许以具体 Schema 的 additionalProperties 为准。PlanValidator 又追加场景可执行约束，因此 schema valid 不等于可执行。

## 关键字段的维护语义

- request_id 关联模型请求/响应；command_id 关联用户命令生命周期；step/source_step 关联编译后的内部执行。不可只保留一个 ID。
- deadline/valid_until 按包含截止边界处理，到达即过期；模型等待时钟与 CARLA 仿真秒不得混算。
- RGB 坐标、canonical y-left、CARLA y-right 各有定义。转换入口必须明确，不能在 B/D 再额外翻转一次。
- target ID 表示当前目标身份；Student 输出的是指针索引，由 Adapter 还原 ID，不能把动态字符串 ID 当分类类别。
- 命令反馈“完成”与场景评分“通过”不同，前者不能作为后者的替代。

## 冻结指纹的用途

[frozen_contracts](../../../challenge/planner/frozen_contracts.py) 对 Schema 规范化 JSON 计算 hash，避免换行差异造成伪漂移。修改真实字段后 hash 必然改变；直接更新 expected hash 让检查通过并没有解决上下游兼容。

后续改接口应先查 [INTERFACES](../INTERFACES.md) 的生产者/消费者矩阵，决定是可兼容增加还是必须新版本，再维护 Schema、示例、Adapter、模型/标签和测试。历史证据仍属于原契约，不能改旧报告 hash 冒充新验证。
