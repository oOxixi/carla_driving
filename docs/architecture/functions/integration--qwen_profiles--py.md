# qwen_profiles：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[integration/qwen_profiles.py](../../../integration/qwen_profiles.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Immutable Qwen model profiles shared by remote serving and evaluation.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `QwenModelProfile.name: str`；默认：`未在声明处设置`。
- `QwenModelProfile.model: str`；默认：`未在声明处设置`。
- `QwenModelProfile.revision: str`；默认：`未在声明处设置`。
- `QwenModelProfile.quantization: str`；默认：`未在声明处设置`。
- `QwenModelProfile.required_linear_kernel: str | None`；默认：`未在声明处设置`。
- `QwenModelProfile.image_max_side: int`；默认：`未在声明处设置`。
- `QwenModelProfile.visual_tokens: int`；默认：`未在声明处设置`。
- `QwenModelProfile.port: int`；默认：`未在声明处设置`。
- `QwenModelProfile.prompt_style: str`；默认：`未在声明处设置`。
- `QwenModelProfile.optional: bool`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

<a id="fn-qwenmodelprofile"></a>

### `QwenModelProfile`

源码位置：[integration/qwen_profiles.py 第 9 行](../../../integration/qwen_profiles.py#L9)。类型：`ClassDef`。

冻结的远端 Qwen3-VL-2B 部署配置：模型与 revision、量化/内核、图像尺寸、token 上限、端口和 prompt 名。属于旧版离散动作后端配置，不代表当前 Teacher Qwen3.5 服务配置，也不会在构造时下载模型。

<a id="fn-get-qwen-profile"></a>

### `get_qwen_profile`

源码位置：[integration/qwen_profiles.py 第 50 行](../../../integration/qwen_profiles.py#L50)。类型：`FunctionDef`。

```python
get_qwen_profile(name: str) -> QwenModelProfile
```

按 profile 名精确查预置表，未知名称抛 ValueError；返回共享冻结配置对象，不从环境覆盖单个字段。

<a id="fn-get-qwen-profile-by-model"></a>

### `get_qwen_profile_by_model`

源码位置：[integration/qwen_profiles.py 第 57 行](../../../integration/qwen_profiles.py#L57)。类型：`FunctionDef`。

```python
get_qwen_profile_by_model(model: str) -> QwenModelProfile
```

按模型 ID 精确匹配预置 profile，未登记模型抛 ValueError；不能用任意兼容 OpenAI 的 model 名直接绕过 profile 约束。

<a id="fn-resolve-qwen-profile"></a>

### `resolve_qwen_profile`

源码位置：[integration/qwen_profiles.py 第 64 行](../../../integration/qwen_profiles.py#L64)。类型：`FunctionDef`。

```python
resolve_qwen_profile(name: str | None) -> QwenModelProfile
```

优先显式 truthy name，其次环境变量 QWEN_PROFILE，最后 int4 默认项；调用 get_qwen_profile，因此不存在的环境配置会报错而非静默回退。

## 内部调用与异常路径

- `get_qwen_profile` 调用：`ValueError`.
- `get_qwen_profile_by_model` 调用：`ValueError`, `_PROFILES.values`.
- `resolve_qwen_profile` 调用：`get_qwen_profile`, `os.getenv`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `get_qwen_profile`，第 54 行：`ValueError(f'unsupported Qwen profile: {name}')`。
- `get_qwen_profile_by_model`，第 61 行：`ValueError(f'unsupported Qwen 2B model: {model}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/qwen_remote_backend.py](../../../integration/qwen_remote_backend.py)
- [integration/scenario_runner_agent.py](../../../integration/scenario_runner_agent.py)
- [integration/tests/test_qwen_profiles.py](../../../integration/tests/test_qwen_profiles.py)
- [tools/run_four_modal_full_chain.py](../../../tools/run_four_modal_full_chain.py)
- [tools/run_long_stability.py](../../../tools/run_long_stability.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-qwen-profiles-py"></a>

### `integration/qwen_profiles.py`

来源 SHA256：`8e65641153e3ab93448fd4d80cd3f658696aa6a0146035fb420c161fef0537bb`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `QwenModelProfile.name` | `str` | `无声明默认；构造/赋值方提供` |
| `QwenModelProfile.model` | `str` | `无声明默认；构造/赋值方提供` |
| `QwenModelProfile.revision` | `str` | `无声明默认；构造/赋值方提供` |
| `QwenModelProfile.quantization` | `str` | `无声明默认；构造/赋值方提供` |
| `QwenModelProfile.required_linear_kernel` | `str &#124; None` | `无声明默认；构造/赋值方提供` |
| `QwenModelProfile.image_max_side` | `int` | `无声明默认；构造/赋值方提供` |
| `QwenModelProfile.visual_tokens` | `int` | `无声明默认；构造/赋值方提供` |
| `QwenModelProfile.port` | `int` | `无声明默认；构造/赋值方提供` |
| `QwenModelProfile.prompt_style` | `str` | `无声明默认；构造/赋值方提供` |
| `QwenModelProfile.optional` | `bool` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `get_qwen_profile` / 54 | `except KeyError` | `raise ValueError(f'unsupported Qwen profile: {name}') from exc` |
| `get_qwen_profile_by_model` / 61 | `本地无直接if；检查上下文` | `raise ValueError(f'unsupported Qwen 2B model: {model}')` |

### 环境参数读取位置

这里只记录源码表达式，不读取当前进程环境；缓存与覆盖关系需查调用时机。

| 来源/行 | 环境变量表达式 | 源码fallback |
|---|---|---|
| `integration/qwen_profiles.py:65` | `'QWEN_PROFILE'` | `'qwen3vl-2b-int4'` |

## 两份预置profile的具体身份

| name | model | revision | quantization / kernel | optional |
|---|---|---|---|---|
| qwen3vl-2b-int4 | h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4 | f91db2369bd00e7ec20bf09b6a0080cdb26aefa5 | gptq / MarlinLinearKernel | False |
| qwen3vl-2b-fp8 | Qwen/Qwen3-VL-2B-Instruct-FP8 | 46485250d8854c0a9be4f1adbc67ca47e5bb6fa5 | fp8 / None | True |

两者image_max_side=256、visual_tokens=64、port=8001、prompt_style=compact-v2。resolve_qwen_profile的默认完整名称是qwen3vl-2b-int4；这里只选择配置，不检测已启动服务是否确实加载相同revision/kernel，运行证据仍需服务manifest。
