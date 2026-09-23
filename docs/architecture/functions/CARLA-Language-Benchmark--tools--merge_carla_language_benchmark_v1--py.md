# merge_carla_language_benchmark_v1：功能记录

上级模块：[模块说明](../modules/support-delivery.md) · 实现：[CARLA-Language-Benchmark/tools/merge_carla_language_benchmark_v1.py](../../../CARLA-Language-Benchmark/tools/merge_carla_language_benchmark_v1.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [运行入口、依赖和产物维护](environment-delivery.md)

## 功能职责与范围

merge_carla_language_benchmark_v1

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `load_json`

源码位置：[CARLA-Language-Benchmark/tools/merge_carla_language_benchmark_v1.py 第 107 行](../../../CARLA-Language-Benchmark/tools/merge_carla_language_benchmark_v1.py#L107)。类型：`FunctionDef`。

```python
load_json(path) -> 未声明返回类型
```

【load_json】从参数、文件、环境或缓存解析运行环境、数据发布或交付所需输入；路径优先级、默认值和缺失处理以函数体为准，读取成功不自动证明内容身份正确。

### `save_json`

源码位置：[CARLA-Language-Benchmark/tools/merge_carla_language_benchmark_v1.py 第 117 行](../../../CARLA-Language-Benchmark/tools/merge_carla_language_benchmark_v1.py#L117)。类型：`FunctionDef`。

```python
save_json(path, data) -> 未声明返回类型
```

【save_json】生成或记录运行环境、数据发布或交付的文件/元数据；执行前要核对目标路径与覆盖行为，执行后以内容哈希、返回码和消费方复核，不能仅以文件存在判定通过。

### `main`

源码位置：[CARLA-Language-Benchmark/tools/merge_carla_language_benchmark_v1.py 第 139 行](../../../CARLA-Language-Benchmark/tools/merge_carla_language_benchmark_v1.py#L139)。类型：`FunctionDef`。

```python
main() -> 未声明返回类型
```

【main】是运行环境、数据发布或交付的执行/命令入口；参数来自紧邻签名或本页CLI表，可能读取外部资源、写产物或启动服务，应以退出码、原始日志和固定输入身份判定结果。

## 内部调用与异常路径

- `load_json` 调用：`json.load`, `open`.
- `save_json` 调用：`json.dump`, `open`, `os.makedirs`, `os.path.dirname`.
- `main` 调用：`Counter`, `FileNotFoundError`, `datetime.now`, `datetime.now().isoformat`, `dict`, `enumerate`, `json.dumps`, `len`, `load_json`, `merged.append`, `os.path.exists`, `print`, `save_json`, `x.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 151 行：`FileNotFoundError(path)`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-delivery.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `CARLA-Language-Benchmark/tools/merge_carla_language_benchmark_v1.py`

来源 SHA256：`75f9326b0eb8a6ccefb9fa66ab72f13e50835dc7fed5c85cd2ebe1242b540349`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `main` / 151 | `not os.path.exists(path)` | `raise FileNotFoundError(path)` |
