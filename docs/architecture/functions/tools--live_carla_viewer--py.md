# live_carla_viewer：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/live_carla_viewer.py](../../../tools/live_carla_viewer.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Read-only CARLA chase camera with live command subtitles.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `FrameStore`

源码位置：[tools/live_carla_viewer.py 第 21 行](../../../tools/live_carla_viewer.py#L21)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `FrameStore.__init__`

源码位置：[tools/live_carla_viewer.py 第 22 行](../../../tools/live_carla_viewer.py#L22)。类型：`FunctionDef`。

```python
FrameStore.__init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `FrameStore.publish`

源码位置：[tools/live_carla_viewer.py 第 27 行](../../../tools/live_carla_viewer.py#L27)。类型：`FunctionDef`。

```python
FrameStore.publish(self, jpeg: bytes) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `FrameStore.wait_after`

源码位置：[tools/live_carla_viewer.py 第 33 行](../../../tools/live_carla_viewer.py#L33)。类型：`FunctionDef`。

```python
FrameStore.wait_after(self, sequence: int, timeout: float=2.0) -> tuple[int, bytes | None]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandStore`

源码位置：[tools/live_carla_viewer.py 第 40 行](../../../tools/live_carla_viewer.py#L40)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandStore.__init__`

源码位置：[tools/live_carla_viewer.py 第 41 行](../../../tools/live_carla_viewer.py#L41)。类型：`FunctionDef`。

```python
CommandStore.__init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandStore.publish`

源码位置：[tools/live_carla_viewer.py 第 51 行](../../../tools/live_carla_viewer.py#L51)。类型：`FunctionDef`。

```python
CommandStore.publish(self, record: dict[str, Any], log_file: Path) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandStore.snapshot`

源码位置：[tools/live_carla_viewer.py 第 69 行](../../../tools/live_carla_viewer.py#L69)。类型：`FunctionDef`。

```python
CommandStore.snapshot(self) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ego_vehicle`

源码位置：[tools/live_carla_viewer.py 第 79 行](../../../tools/live_carla_viewer.py#L79)。类型：`FunctionDef`。

```python
ego_vehicle(world: carla.World) -> carla.Vehicle | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `encode_frame`

源码位置：[tools/live_carla_viewer.py 第 86 行](../../../tools/live_carla_viewer.py#L86)。类型：`FunctionDef`。

```python
encode_frame(image: carla.Image, ego: carla.Vehicle) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_latest_log`

源码位置：[tools/live_carla_viewer.py 第 103 行](../../../tools/live_carla_viewer.py#L103)。类型：`FunctionDef`。

```python
_latest_log(log_dir: Path, scenario_id: str) -> Path | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `watch_commands`

源码位置：[tools/live_carla_viewer.py 第 108 行](../../../tools/live_carla_viewer.py#L108)。类型：`FunctionDef`。

```python
watch_commands(log_dir: Path, scenario_id: str, command_log: Path | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `Handler`

源码位置：[tools/live_carla_viewer.py 第 187 行](../../../tools/live_carla_viewer.py#L187)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `Handler.log_message`

源码位置：[tools/live_carla_viewer.py 第 188 行](../../../tools/live_carla_viewer.py#L188)。类型：`FunctionDef`。

```python
Handler.log_message(self, _format: str, *_args: object) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `Handler.do_GET`

源码位置：[tools/live_carla_viewer.py 第 191 行](../../../tools/live_carla_viewer.py#L191)。类型：`FunctionDef`。

```python
Handler.do_GET(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/live_carla_viewer.py 第 231 行](../../../tools/live_carla_viewer.py#L231)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `ego_vehicle` 调用：`actor.attributes.get`, `world.get_actors`, `world.get_actors().filter`.
- `encode_frame` 调用：`FRAMES.publish`, `Image.frombuffer`, `Image.frombuffer('RGBA', (image.width, image.height), image.raw_data, 'raw', 'BGRA', 0, 1).convert`, `ImageDraw.Draw`, `draw.rectangle`, `draw.text`, `ego.get_velocity`, `frame.save`, `io.BytesIO`, `output.getvalue`.
- `_latest_log` 调用：`list`, `log_dir.glob`, `max`, `path.stat`.
- `watch_commands` 调用：`COMMANDS.publish`, `STOP.wait`, `_latest_log`, `command_log.is_file`, `json.loads`, `latest.open`, `record.get`, `stream.close`, `stream.readline`, `stream.seek`, `stream.tell`.
- `main` 调用：`STOP.is_set`, `STOP.set`, `STOP.wait`, `ThreadingHTTPServer`, `argparse.ArgumentParser`, `args.command_log.resolve`, `args.log_dir.resolve`, `blueprint.set_attribute`, `camera.destroy`, `camera.listen`, `camera.stop`, `carla.Client`, `carla.Location`, `carla.Rotation`, `carla.Transform`, `client.get_world`, `client.set_timeout`, `ego_vehicle`, `encode_frame`, `parser.add_argument`, `parser.parse_args`, `print`, `server.server_close`, `server.shutdown`, `str`, `threading.Thread`, `threading.Thread(target=server.serve_forever, daemon=True).start`, `threading.Thread(target=watch_commands, args=(args.log_dir.resolve(), args.scenario_id, args.command_log.resolve() if args.command_log is not None else None), daemon=True).start`, `time.sleep`, `world.get_blueprint_library`, `world.get_blueprint_library().find`, `world.spawn_actor`.
- `__init__` 调用：`threading.Condition`, `threading.Lock`.
- `publish` 调用：`command_id.strip`, `int`, `isinstance`, `record.get`, `self.condition.notify_all`, `source_text.strip`, `str`.
- `wait_after` 调用：`self.condition.wait`.
- `snapshot` 调用：`dict`.
- `do_GET` 调用：`COMMANDS.snapshot`, `FRAMES.wait_after`, `STOP.is_set`, `json.dumps`, `json.dumps(COMMANDS.snapshot(), ensure_ascii=False).encode`, `len`, `self.end_headers`, `self.send_error`, `self.send_header`, `self.send_response`, `self.wfile.flush`, `self.wfile.write`, `str`, `str(len(jpeg)).encode`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 233 行：`parser.add_argument('--host', default='127.0.0.1')`。
- 第 234 行：`parser.add_argument('--carla-port', type=int, default=2000)`。
- 第 235 行：`parser.add_argument('--http-port', type=int, default=18081)`。
- 第 236 行：`parser.add_argument('--width', type=int, default=1280)`。
- 第 237 行：`parser.add_argument('--height', type=int, default=720)`。
- 第 238 行：`parser.add_argument('--log-dir', type=Path, required=True)`。
- 第 239 行：`parser.add_argument('--command-log', type=Path, help='runner console log containing canonical_command_route records')`。
- 第 243 行：`parser.add_argument('--scenario-id', default='OFFICIAL_S2_COMPLEX_AVOIDANCE_8KM')`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/live_carla_viewer.py`

来源 SHA256：`c9e24befde6e627f4ec7c39105fa46b1e5c1fc8580e0e7f9de1ec0d734e1b95c`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 233 | `'--host'` | `default='127.0.0.1'` |
| 234 | `'--carla-port'` | `type=int; default=2000` |
| 235 | `'--http-port'` | `type=int; default=18081` |
| 236 | `'--width'` | `type=int; default=1280` |
| 237 | `'--height'` | `type=int; default=720` |
| 238 | `'--log-dir'` | `type=Path; required=True` |
| 239 | `'--command-log'` | `type=Path; help='runner console log containing canonical_command_route records'` |
| 243 | `'--scenario-id'` | `default='OFFICIAL_S2_COMPLEX_AVOIDANCE_8KM'` |
