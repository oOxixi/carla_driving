# 验证范围与复核步骤

返回[项目导航](README.md)。所有命令从当前工作树根目录运行。

## 来源哈希口径

逐文件页的“来源 SHA256”以及 `inventory.json` 中的 `sha256` 均以 Git blob 原始字节为输入，而不是当前工作区文件字节。验证等价于读取 `git show HEAD:<path>` 后计算 SHA256。这样 `.gitattributes`、`core.autocrlf` 或操作系统换行转换不会制造虚假的源码漂移。

文件清单仍是标注日期的静态快照；哈希一致只证明清单内记录与目标提交一致，不表示快照日期后新增文件已经自动进入模块分类。新增源码、配置或文档时仍需更新清单、模块页和追踪矩阵。

## 静态覆盖记录

清单列出所有 Git 跟踪及未忽略本地文件，逐个归属；对 Python 解析定义/签名/import/CLI，对脚本、配置、Schema 记录内容指纹。
数据/图片/模型/报告逐文件登记类别，但不把数据条目视为业务函数。第三方二进制内部与运行时动态调用不在静态分析能力内。
本次用临时只读分析生成清单并检查链接；没有保留执行工具或改变项目测试门禁。重复定义仅记录，没有删除。

## 测试选择

默认 [pytest.ini](../../pytest.ini) 只发现 A/B/C/D、integration、voice_group 的指定测试目录；不能把裸 `pytest` 通过视作全项目通过。

| 功能 | 验证入口 | 前提 / 解释 |
|---|---|---|
| 基础车控 | `py -3.12 -m pytest -q car_control_A/tests car_control_B/tests car_control_C/tests car_control_D/tests integration/tests` | 多数使用 mock；真实 CARLA 仍需场景闭环 |
| 语音 | `py -3.12 -m pytest -q voice_group/tests` | 音频模型/权重相关路径需额外环境 |
| Qwen HTTP | `py -3.12 -m pytest -q qwen_service/tests` | 当前存在旧测试导入失败，见台账 |
| A1 结构与交付 | `py -3.12 -m pytest -q challenge/tests` | torch、ONNX、ORT；本轮前拉取验证 26 项通过 |
| 蒸馏 | `py -3.12 -m pytest -q challenge/distillation/tests` | 训练依赖；mock smoke 不代表训练精度 |
| B1 数据治理 | `py -3.12 -m pytest -q challenge/dataset/tests` | collector、split、release、D2/D3 与训练视图 |
| HIL | `py -3.12 -m pytest -q challenge/hil/tests` | fake Runtime 测试不代表真实板端 trace 可用 |
| 全部 Python 测试发现 | 通过 inventory 中 `kind=test` 枚举；显式传入实际目录 | 先 collect-only 发现导入/依赖/命名冲突，再运行相应集合 |
| 场景合同 | `py -3.12 tools/validate_scenarios.py`、`py -3.12 tools/validate_official_scenes.py` | 静态场景规则，不证明驾驶完成 |
| 泛化 | `py -3.12 tools/run_generalization_gate.py` | holdout 只用于冻结评估，不反复调参 |
| 模型产物 | `py -3.12 -m challenge.export.validate_artifacts --root .` | SHA/结构一致性；不等于蒸馏精度/J6P 转换通过 |
| CARLA / J6P | 模块手册所列真实环境命令 | 本轮不启动仿真、不训练、不占用板卡；需单独的真实证据 |

## 本轮审计原则

对 Git 跟踪的全部 141 个 test_*.py 文件做显式 collect-only：1373 项被发现，3 处收集错误。两处为缺 soundfile 依赖，一处为旧 create_server 导入；这是发现结果，未执行全部 1373 项测试。

- 对确定代码矛盾记录源码位置、触发条件和可复现结果；仅有推断标记“待证”。
- 不自动启用完整测试目录：旧测试/可选依赖会使默认 CI 语义改变，应先修复并协商 Gate。
- 不重新生成冻结数据、训练权重、历史结果来“统一”清单。
- 审计原始临时输出保存在 `artifacts/`；可共享结论写入[台账](AUDIT.md)。

## 2026-09-20 诊断文档增补验证

新增2份横向索引、5份功能记录，20个业务模块均链接追踪矩阵和诊断入口；重点模块直接索引专项功能页。全architecture Markdown本地链接检查8742处，失效0；新增中文文件已检查UTF-8内容。未重跑业务测试或CARLA，未更改业务实现。

此次走查验证了场景漂移、STOP目标构造、验收合成和通用告警的代码定位路径。A03实际failed_keys、long首次故障及Wave2运行身份仍缺，明确记录在W2台账；这些是运行证据缺口，不以文档交付宣称根因闭合。源码inventory保持原快照。

## 20模块接口与参数复核

详见[逐模块复核记录](MODULE_REVIEW.md)：区分源码声明、配置文件值、实际生效参数和运行验收。当前逐文件页358份、语义功能页26份；此前阶段计数不替代本次实际遍历结果。
