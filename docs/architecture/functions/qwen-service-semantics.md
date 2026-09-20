# Qwen 服务模式、确定性组装与健康状态

上级：[Qwen 后端模块](../modules/support-qwen.md)。

## 服务端不是所有模型路径的统称

[server.py](../../../qwen_service/server.py) 通过 QwenHTTPServer 持有 QwenDecisionService；[service.py](../../../qwen_service/service.py) 有不同 Backend。车侧 [QwenServiceClient](../../../integration/qwen_service_client.py) 与直接 OpenAI-compatible Backend 是不同接入位置。修改一条路径不会自动修改所有入口。

## vLLM Planner 当前如何输出计划

`VllmQwenPlannerBackend` 把请求组织成受限动作选择，模型返回短选择，随后由代码确定性组装 ManeuverPlan。构造函数虽然接受 max_new_tokens，当前实现固定 `self.max_new_tokens=1`；图像边长固定 224，传入其他值会拒绝。

因此，一条 Plan 的来源包含模型选择和代码组装逻辑。增加行为类别时需要同时看 `_CHOICES`、候选筛选、prompt、组装、PlanValidator 与执行器，不能只让模型“自由输出一个新枚举”。

## health / production_ready 的当前限制

类级 production_ready=True，health 返回“endpoint configured”，没有请求后端探测。实际最小复现中连 `_client` 都未初始化仍返回 True。它目前只能说明该方法的状态声明，不能证明模型可达、加载正确或已有生产评测。

这是一项待修问题，本轮不改变接口。将来改 health 要同时读 runtime.healthcheck、客户端调用及服务响应结构；应明确配置完成、可用性、模型身份和评测 Gate 四种状态，而不是用一个布尔值替代全部事实。

## 验证定位

[integration Qwen tests](../../../integration/tests/test_qwen_service.py) 覆盖多个 Backend 行为；[qwen_service/tests](../../../qwen_service/tests) 中 test_server 仍导入已删除 create_server，当前收集失败。修改服务构造接口时，须同时维护这组旧测试与 HTTP 使用方，裸 pytest 不会默认发现它。
