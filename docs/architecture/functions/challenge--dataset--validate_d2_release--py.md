# validate_d2_release：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/validate_d2_release.py](../../../challenge/dataset/validate_d2_release.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

Read-only integrity gate for the portable B1 D2 release.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_sha256`

源码位置：[challenge/dataset/validate_d2_release.py 第 25 行](../../../challenge/dataset/validate_d2_release.py#L25)。类型：`FunctionDef`。

```python
_sha256(path: Path) -> str
```

`_sha256` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `_canonical_text_bytes`

源码位置：[challenge/dataset/validate_d2_release.py 第 33 行](../../../challenge/dataset/validate_d2_release.py#L33)。类型：`FunctionDef`。

```python
_canonical_text_bytes(path: Path) -> bytes
```

Match Git's LF-normalized text blob on both Windows and Linux.

### `canonical_text_sha256`

源码位置：[challenge/dataset/validate_d2_release.py 第 38 行](../../../challenge/dataset/validate_d2_release.py#L38)。类型：`FunctionDef`。

```python
canonical_text_sha256(path: Path) -> str
```

`canonical_text_sha256` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `validate_release`

源码位置：[challenge/dataset/validate_d2_release.py 第 42 行](../../../challenge/dataset/validate_d2_release.py#L42)。类型：`FunctionDef`。

```python
validate_release(release_dir: Path, *, check_images: bool=True) -> dict[str, Any]
```

`validate_release` 执行当前阶段的拒绝式门禁；只覆盖函数读取的字段/文件，成功不能替代Teacher服务、闭环终态、切分防泄漏或下游A3预检。

### `main`

源码位置：[challenge/dataset/validate_d2_release.py 第 183 行](../../../challenge/dataset/validate_d2_release.py#L183)。类型：`FunctionDef`。

```python
main() -> int
```

解析命令行参数并编排本脚本的数据读取、身份校验、生成/采集与落盘步骤；退出码和产物是否可发布取决于本页所列拒绝条件，不能只凭文件生成成功判定。

## 内部调用与异常路径

- `_sha256` 调用：`digest.hexdigest`, `digest.update`, `hashlib.sha256`, `iter`, `path.open`, `stream.read`.
- `_canonical_text_bytes` 调用：`path.read_bytes`, `path.read_bytes().replace`.
- `canonical_text_sha256` 调用：`_canonical_text_bytes`, `hashlib.sha256`, `hashlib.sha256(_canonical_text_bytes(path)).hexdigest`.
- `validate_release` 调用：`''.join`, `''.join((f'{path.name}\t{_sha256(path)}\n' for path in sorted(published_images, key=lambda p: p.name))).encode`, `(release_dir / 'images').resolve`, `(release_dir / 'split_report.json').read_text`, `(repo_root / rgb_ref).resolve`, `(row.get('model_request') or {}).get`, `Counter`, `_canonical_text_bytes`, `_sha256`, `dict`, `enumerate`, `errors.append`, `groups.add`, `hashlib.sha256`, `hashlib.sha256(canonical).hexdigest`, `hashlib.sha256(content).hexdigest`, `ids.add`, `image_path.is_file`, `image_path.is_relative_to`, `image_path.stat`, `images_dir.glob`, `json.loads`, `len`, `manifest['counts'].get`, `manifest['files'].items`, `manifest_path.read_text`, `path.is_file`, `path.open`, `quarantine_path.is_file`, `quarantine_path.open`, `raw.strip`, `referenced_images.add`, `release_dir.resolve`, `roles.items`, `row.get`, `row.get('metadata', {}).get`, `row.get('quality', {}).get`, `set`, `signed_manifest_path.is_file`, `sorted`, `str`, `teachers.items`, `versions.items`, `visual.get`.
- `main` 调用：`argparse.ArgumentParser`, `args.output.parent.mkdir`, `args.output.write_text`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`, `validate_release`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 185 行：`parser.add_argument('--release-dir', default='challenge/dataset/releases/d2_v1_1', type=Path)`。
- 第 188 行：`parser.add_argument('--skip-images', action='store_true')`。
- 第 189 行：`parser.add_argument('--output', type=Path)`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [challenge/dataset/build_a3_d2_view.py](../../../challenge/dataset/build_a3_d2_view.py)
- [challenge/dataset/tests/test_validate_d2_release.py](../../../challenge/dataset/tests/test_validate_d2_release.py)
- [challenge/distillation/audit_d2_view.py](../../../challenge/distillation/audit_d2_view.py)
- [challenge/distillation/train.py](../../../challenge/distillation/train.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-data.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/dataset/validate_d2_release.py`

来源 SHA256：`b4272a7b5afac019d406a7bcdcabb187e2a52a3866ced3a5c64a252fada4a43b`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 185 | `'--release-dir'` | `default='challenge/dataset/releases/d2_v1_1'; type=Path` |
| 188 | `'--skip-images'` | `action='store_true'` |
| 189 | `'--output'` | `type=Path` |
