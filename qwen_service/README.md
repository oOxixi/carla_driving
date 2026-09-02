# Qwen 服务边界

本包提供 CARLA runner 使用的 HTTP 客户端、服务协议、健康检查和兼容本地服务实现。
正式比赛只允许连接生产就绪的 Qwen 2B 服务；`/health` 必须返回 `READY` 且
`production_ready=true`。

接口：

- `GET /health`：模型、后端和生产就绪状态。
- `POST /infer`：接收结构化感知与指令，返回经 schema 校验的高层计划。
- `GET /metrics`：请求计数、延迟和在途请求。

超时、并发满、模型错误、低置信度和非法输出均 fail-closed，不会转成车辆控制。正式
S1/S2/S3 通过 `--qwen-service-url` 接入；启动命令和固定 2B 配置见
`docs/runbooks/QWEN_REMOTE.md`，完整场景命令见 `docs/runbooks/SECOND_GROUP.md`。

本包中保留的 Transformers 实现只用于协议级兼容测试，不能代替正式远程 2B 服务生成
比赛证据。
