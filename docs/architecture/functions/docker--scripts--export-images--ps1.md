# export-images：功能记录

上级模块：[模块说明](../modules/support-delivery.md) · 实现：[docker/scripts/export-images.ps1](../../../docker/scripts/export-images.ps1)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [运行入口、依赖和产物维护](environment-delivery.md)

## 功能职责与范围

export-images

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

入口相关声明（cwd、参数、环境、模块调用、容器指令）；仅用于定位，需结合模块说明判断当前可用性：

- 第 2 行：`param(`
- 第 17 行：`docker image inspect $image *> $null`
- 第 23 行：`docker image save --output $archive @images`
- 第 24 行：`if ($LASTEXITCODE -ne 0) { throw "docker image save failed." }`

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

### `docker/scripts/export-images.ps1`

来源 SHA256：`b245e8cda65f726d8b88c5f2af92de806901ac6f08005d6c279039fd04fdded1`。

非Python/Schema资源：已核对内容指纹与来源存在性；参数生效和业务语义不能由指纹证明，参见所属模块与原资源记录。

### 脚本参数与转发原文

以下摘录参数声明、变量默认及参数转发位置；赋值变量不全是外部CLI。Shell环境fallback与PowerShell param类型由脚本解释，不套用argparse规则。未执行脚本。

```powershell
# L2
param(
# L3
    [string]$ControllerImage = "carla-driving-controller:0.1.0",
# L4
    [string]$CarlaImage = "carlasim/carla:0.9.16",
# L5
    [string]$OutputDirectory = "artifacts",
# L6
    [switch]$IncludeCarla
# L7
)
```
