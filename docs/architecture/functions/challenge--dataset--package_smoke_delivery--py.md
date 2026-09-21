# package_smoke_delivery：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/package_smoke_delivery.py](../../../challenge/dataset/package_smoke_delivery.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

package_smoke_delivery

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[challenge/dataset/package_smoke_delivery.py 第 19 行](../../../challenge/dataset/package_smoke_delivery.py#L19)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `read_jsonl`

源码位置：[challenge/dataset/package_smoke_delivery.py 第 29 行](../../../challenge/dataset/package_smoke_delivery.py#L29)。类型：`FunctionDef`。

```python
read_jsonl(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `copy_verified`

源码位置：[challenge/dataset/package_smoke_delivery.py 第 57 行](../../../challenge/dataset/package_smoke_delivery.py#L57)。类型：`FunctionDef`。

```python
copy_verified(src: Path, dst: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `relative_to_root`

源码位置：[challenge/dataset/package_smoke_delivery.py 第 78 行](../../../challenge/dataset/package_smoke_delivery.py#L78)。类型：`FunctionDef`。

```python
relative_to_root(path: Path, root: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/package_smoke_delivery.py 第 88 行](../../../challenge/dataset/package_smoke_delivery.py#L88)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `read_jsonl` 调用：`FileNotFoundError`, `ValueError`, `enumerate`, `isinstance`, `json.loads`, `line.strip`, `path.is_file`, `path.open`, `rows.append`.
- `copy_verified` 调用：`FileNotFoundError`, `dst.as_posix`, `dst.parent.mkdir`, `dst.stat`, `sha256_file`, `shutil.copy2`, `src.is_file`.
- `relative_to_root` 调用：`path.as_posix`, `path.relative_to`, `path.relative_to(root).as_posix`.
- `main` 调用：`'\n'.join`, `(output_dir / 'README.md').write_text`, `(repo_root / output_dir_arg).resolve`, `Path`, `Path(args.repo_root).expanduser`, `Path(args.repo_root).expanduser().resolve`, `RuntimeError`, `SystemExit`, `argparse.ArgumentParser`, `copy_verified`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `delivery_manifest_path.write_text`, `directory.mkdir`, `isinstance`, `json.dumps`, `len`, `missing_rgb.append`, `output_dir_arg.is_absolute`, `output_dir_arg.resolve`, `packaged_path.relative_to`, `packaged_path.relative_to(output_dir).as_posix`, `parser.add_argument`, `parser.parse_args`, `print`, `read_jsonl`, `relative_to_root`, `rgb_entries.append`, `rgb_manifest_path.write_text`, `sample.get`, `sha256_file`, `shutil.copy2`, `source_dir.is_dir`, `source_files.items`, `src_rgb.is_absolute`, `src_rgb.is_file`, `src_rgb.resolve`, `src_rgb.stat`, `src_rgb.suffix.lower`, `visual.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `copy_verified`，第 62 行：`FileNotFoundError(src)`。
- `main`，第 126 行：`SystemExit(f'SOURCE_DATASET_DIR_NOT_FOUND={source_dir}')`。
- `main`，第 262 行：`RuntimeError(f'EXPECTED_30_RAW_SAMPLES_GOT={len(raw_samples)}')`。
- `main`，第 267 行：`RuntimeError(f'EXPECTED_28_TRAIN_ELIGIBLE_GOT={len(train_eligible)}')`。
- `main`，第 273 行：`RuntimeError(f'EXPECTED_2_HARD_CASES_GOT={len(hard_cases)}')`。
- `main`，第 278 行：`RuntimeError(f'EXPECTED_22_TRAIN_GOT={len(train_rows)}')`。
- `main`，第 283 行：`RuntimeError(f'EXPECTED_6_VAL_GOT={len(val_rows)}')`。
- `main`，第 292 行：`RuntimeError('TRAIN_VAL_PARTITION_MISMATCH')`。
- `main`，第 345 行：`RuntimeError(f'RGB_SHA256_MISMATCH sample={sample_id} expected={expected_sha} actual={actual_sha}')`。
- `main`，第 401 行：`RuntimeError('RGB_PACKAGING_INCOMPLETE')`。
- `read_jsonl`，第 33 行：`FileNotFoundError(path)`。
- `read_jsonl`，第 43 行：`ValueError(f'{path}:{line_no}: invalid JSON: {exc}')`。
- `read_jsonl`，第 48 行：`ValueError(f'{path}:{line_no}: row is not object')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 91 行：`parser.add_argument('--repo-root', default='.')`。
- 第 96 行：`parser.add_argument('--output-dir', default='challenge/dataset/smoke_v0')`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-data.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/dataset/package_smoke_delivery.py`

来源 SHA256：`888457f041f32bb72c77caa8bf072ed4221d40ac3b523d2c6d3a58bdb6c66fc2`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 91 | `'--repo-root'` | `default='.'` |
| 96 | `'--output-dir'` | `default='challenge/dataset/smoke_v0'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `read_jsonl` / 33 | `not path.is_file()` | `raise FileNotFoundError(path)` |
| `read_jsonl` / 43 | `except json.JSONDecodeError` | `raise ValueError(f'{path}:{line_no}: invalid JSON: {exc}') from exc` |
| `read_jsonl` / 48 | `not isinstance(row, dict)` | `raise ValueError(f'{path}:{line_no}: row is not object')` |
| `copy_verified` / 62 | `not src.is_file()` | `raise FileNotFoundError(src)` |
| `main` / 126 | `not source_dir.is_dir()` | `raise SystemExit(f'SOURCE_DATASET_DIR_NOT_FOUND={source_dir}')` |
| `main` / 262 | `len(raw_samples) != 30` | `raise RuntimeError(f'EXPECTED_30_RAW_SAMPLES_GOT={len(raw_samples)}')` |
| `main` / 267 | `len(train_eligible) != 28` | `raise RuntimeError(f'EXPECTED_28_TRAIN_ELIGIBLE_GOT={len(train_eligible)}')` |
| `main` / 273 | `len(hard_cases) != 2` | `raise RuntimeError(f'EXPECTED_2_HARD_CASES_GOT={len(hard_cases)}')` |
| `main` / 278 | `len(train_rows) != 22` | `raise RuntimeError(f'EXPECTED_22_TRAIN_GOT={len(train_rows)}')` |
| `main` / 283 | `len(val_rows) != 6` | `raise RuntimeError(f'EXPECTED_6_VAL_GOT={len(val_rows)}')` |
| `main` / 292 | `len(train_rows) + len(val_rows) != len(train_eligible)` | `raise RuntimeError('TRAIN_VAL_PARTITION_MISMATCH')` |
| `main` / 345 | `isinstance(expected_sha, str) and expected_sha != actual_sha` | `raise RuntimeError(f'RGB_SHA256_MISMATCH sample={sample_id} expected={expected_sha} actual={actual_sha}')` |
| `main` / 401 | `missing_rgb` | `raise RuntimeError('RGB_PACKAGING_INCOMPLETE')` |
