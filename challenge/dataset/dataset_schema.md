# B1 Teacher Distillation Dataset Schema

## 1. 目标

本数据集用于挑战赛道 B1 Teacher 数据采集、数据治理以及后续 J6P Student 蒸馏训练。

Teacher 链固定为：

- Teacher Model: `Qwen/Qwen3.5-2B`
- Planner Mode: `planner_v2`
- Input Contract: `ModelRequest V1`
- Output Contract: `ManeuverPlan V2`
- Teacher Adapter Code: 以每条样本中记录的 `teacher_git_sha` 为准

B1 数据采集不得改变：

- CARLA 控制逻辑
- Planner 接口语义
- A/B/C/D 控制链
- SafetySupervisor
- Frozen Test 定义
- 原有场景行为

数据生成采用离线 collector，从已有 ScenarioEvidenceRecorder JSONL 中提取 Teacher supervision。

---

## 2. 有效 Teacher 样本定义

一条有效 Teacher 样本定义为：

ModelRequest V1
+
Teacher 实际使用的 RGB
+
ManeuverPlan V2
+
运行追踪 metadata
+
closed-loop quality evidence

注意：

以下数量均不能直接视为 Teacher sample 数：

- JSONL 行数
- CARLA frame 数
- RGB 图片数量
- 语言句子数量

只有通过完整配对与质量校验的 Teacher supervision event 才计入 effective sample count。

---

## 3. 数据源映射

### 3.1 Teacher 输入

Teacher 输入来自：

canonical_routing
phase = SUBMIT
payload.orchestration.model_request

因此：

sample.model_request
=
SUBMIT.payload.orchestration.model_request

该对象必须完整保留，不得自行重构、删除字段或重新排序 targets。

---

### 3.2 Teacher 输出

Teacher 标签来自：

canonical_routing
phase = RESOLVE
payload.orchestration.decision_plan

因此：

sample.teacher_plan
=
RESOLVE.payload.orchestration.decision_plan

该对象为正式的 ManeuverPlan V2。

不得使用：

payload.orchestration.compiled_plan

代替 Teacher 标签。

原因是 compiled_plan 属于下游执行编译结果，不是原始 Teacher ManeuverPlan V2。

---

## 4. 顶层 Sample Schema

每一条 accepted sample 必须包含：

```json
{
  "dataset_schema_version": "1.0",
  "dataset_version": "teacher_distill_v0.1_smoke",
  "sample_id": "td_xxx",

  "metadata": {},

  "model_request": {},
  "teacher_plan": {},

  "visual_input": {},
  "target_grounding": {},
  "teacher_runtime": {},
  "sample_class": {},
  "closed_loop_quality": {},
  "quality": {}
}

不得使用 JSONL frame 数量替代 sample 数量。

5. sample_id

sample_id 必须稳定来源于该 supervision event 的身份信息。

当前使用：

run_id
command_id
request_id
frame_id

进行 canonical JSON 序列化后计算 SHA256。

格式：

td_<24 hex chars>

sample_id 不允许通过随机 UUID 人为扩充数据量。

6. metadata

metadata 用于数据追踪、版本管理和数据划分。

当前字段：

run_id
recorded_at_utc

scenario_id
scenario_family
difficulty
map
weather
seed

route_hash
group_key

frame_id
sim_time_s

teacher_git_sha
teacher_model_id
teacher_mode
teacher_service_url

request_id
command_id
plan_id

source_log
scenario_config_path
7. Teacher Git SHA

teacher_git_sha 必须来自：

run_start.config.code_version

不得在已有运行日志包含该字段时手动硬编码。

例如当前 Smoke 样本：

a05c8b76efcd4c176965223c661f40b153cb1836

8. Teacher Model ID

teacher_model_id 优先来自：

teacher_plan.model_id

例如：

Qwen/Qwen3.5-2B

teacher_service_url 只是运行环境 provenance。

例如：

http://127.0.0.1:18003

它不能作为 Teacher 模型唯一身份。

9. ModelRequest V1

model_request 必须完整保留 Teacher 实际收到的 ModelRequest。

当前正式版本：

schema_version = "1.0"

核心字段包括：

schema_version
request_id
command_id
created_at_ns
deadline_ns
source_text
scene_summary
targets
constraints

同时可能包含：

command_hint
rgb_ref
routing
scene_capabilities

Collector 不得自行根据语言重新生成 ModelRequest。

10. ManeuverPlan V2

teacher_plan 必须是完整：

ManeuverPlan V2

当前正式版本：

schema_version = "2.0"

必须包含：

schema_version
request_id
command_id
plan_id
plan_type
steps
replan_conditions
confidence
requires_confirmation
created_at_ns
valid_until_ns
reason_code
model_id

必须满足：

plan_type = MANEUVER_SEQUENCE

并且：

1 <= len(steps) <= 4

11. request_id / command_id 对齐

有效样本必须满足：

model_request.request_id

teacher_plan.request_id

并且：

model_request.command_id

teacher_plan.command_id

任一不一致：

quality.valid_for_training = false

对应 rejection：

REQUEST_ID_MISMATCH

或：

COMMAND_ID_MISMATCH

12. RGB 输入

visual_input 保存 Teacher 实际视觉输入的追踪信息。

字段：

rgb_ref
resolved_path
rgb_sha256
size_bytes
available

其中：

rgb_ref

必须对应：

model_request.rgb_ref

有效训练样本必须满足：

available = true

并计算 SHA256 用于完整性验证。

当前已验证 Smoke 图片规格为：

JPEG
224 x 224
RGB

注意：

不能使用“同一场景附近帧”替换 Teacher 实际使用的 RGB。

必须使用 ModelRequest 中明确引用的那一帧。

13. Target Candidates

原始候选目标来自：

model_request.targets

B1 raw dataset 必须严格保留 ModelRequest 中的原始顺序。

禁止按照以下信息重新排序：

Teacher label
target_id 是否被 Teacher 选择
Teacher behavior
confidence
distance
class
人工优先级

尤其禁止根据 Teacher 输出排序，因为这会造成 label leakage。

14. target_id Grounding

Teacher 引用 target 来自：

teacher_plan.steps[*].target.target_id

14.1 No Target

如果：

target_id = null

这是合法的 no-target 样本。

即使 ModelRequest 中存在候选 objects，也不能强行将 Teacher plan 绑定到某个 candidate。

14.2 有 Target

如果 Teacher plan 中：

target_id != null

则该 ID 必须存在于：

model_request.targets[*].target_id

否则：

target_grounding.valid = false

并：

quality.valid_for_training = false

rejection reason：

TARGET_GROUNDING_INVALID

15. target_pointer 规则

Raw B1 dataset 不负责最终固定 Student TopK。

Raw dataset 保存完整：

model_request.targets

后续 Student preprocessing 确定 TopK 后，再生成：

target_pointer

推荐编码：

0 ... K-1 = candidate index
NO_TARGET = 独立 no-target 类

候选 index 必须基于：

ModelRequest 原始 target 顺序

不得基于 Teacher label 重排。

如果：

Teacher target_id 存在

但：

target_id 被 TopK 截断

则必须标记：

TARGET_OUTSIDE_TOPK

不得偷偷映射成：

NO_TARGET

最终 TopK 大小必须由 Student 输入 contract 决定。

16. 数值类型和单位

标准物理单位：

distance_m              meter
relative_speed_mps      meter / second
target_speed_mps        meter / second
speed_limit_mps         meter / second
max_target_speed_mps    meter / second
time_gap_s              second
sim_time_s              second
ttc_s                   second

Student tensor 推荐：

continuous value  -> float32
index / pointer   -> int64
categorical       -> int64
boolean           -> bool 或 int8
17. Missing Value

null 与物理数值 0 含义不同。

例如：

ttc_s = null

不能直接解释为：

ttc_s = 0 second

如果 Student tensor 必须进行数值填充，应使用：

value = 0
valid_mask = 0

实际数值存在时：

value = actual_value
valid_mask = 1
18. Route Identity

场景 route 来自：

run_start.config.config_path

对应的 scenario JSON 中：

route

Collector 对完整 route object 进行 canonical JSON 序列化，然后计算：

route_hash

SHA256(canonical_route_json)[:16]

这样可以在不把完整 route 重复写入每条 metadata 的情况下稳定标识路线。

19. Dataset Group

防止相邻 frame / 同一场景序列泄漏，数据划分不能按单条 row 随机划分。

当前 group 定义：

scenario_family
+
map
+
route_hash
+
seed

上述字段 canonical 化后生成：

group_key

所有相同 group_key 的样本必须进入同一个 split。

禁止：

同一 group 一部分进 Train，另一部分进 Val/Test。

20. Split 原则

正式数据划分必须按 group 划分。

禁止：

random row split
random frame split
neighboring frame split

建议最终：

Train 约 70%
Val   约 15%
Test  约 15%

但 group integrity 优先于精确比例。

不能为了凑精确 70/15/15 而拆 group。

21. Sample Classification

每条样本具有：

sample_class.primary

取值：

NORMAL
COMPLEX
SAFETY_CRITICAL
21.1 NORMAL

典型：

KEEP_LANE
SET_SPEED
普通 STOP
普通 TURN
简单单步 plan
21.2 COMPLEX

典型：

多个 ManeuverPlan steps
FOLLOW
YIELD
AVOID_OBSTACLE
RETURN_TO_LANE
CHANGE_LANE_LEFT
CHANGE_LANE_RIGHT
复杂 compound instruction
21.3 SAFETY_CRITICAL

典型：

risk_level = HIGH
risk_level = EMERGENCY
SafetySupervisor override
紧急行人冲突
紧急避障
安全冲突

Sample class 是数据治理 metadata。

它不能替代正式 Teacher Plan label。

22. Teacher Runtime Metadata

teacher_runtime 可记录：

resolve_disposition
model_timing

model_timing 可能包括：

infer_callback_ms
queue_wait_ms
sensor_to_model_ms
sensor_to_submit_ms
validate_compile_ms

这些数据用于分析 Teacher latency 和采集质量。

B1 Teacher 数据采集不能仅因为 Teacher 推理耗时较高就自动删除监督样本。

Student 部署 latency gate 属于后续挑战部署评测问题。

23. Closed-Loop Quality

closed_loop_quality 从：

MANEUVER_EVENT
run_complete

提取。

字段：

available

run_status
scenario_acceptance_passed

command_terminal_status
plan_terminal_state
plan_terminal_reason

collision_count
lane_invasion_count
route_deviation_count
red_light_violation_count

safety_override_frames
safety_override_observed

min_gap_m
min_ttc_s
24. Command-Level Outcome

不能因为 run_complete 中存在任意：

FAILED

就自动 reject 整条 Teacher sample。

例如内部：

qwen-wait-xxx

可能 FAILED，但 supervision command：

scenario_cmd_xxx

仍然可以：

SUCCEEDED

因此必须使用：

sample.metadata.command_id

查询：

run_complete.summary.command_terminal_statuses

得到该 supervision command 自己的结果。

25. Accepted Sample 最低要求

有效训练样本至少满足：

ModelRequest 存在
ModelRequest.schema_version = 1.0

ManeuverPlan 存在
ManeuverPlan.schema_version = 2.0
ManeuverPlan.plan_type = MANEUVER_SEQUENCE

1 <= len(steps) <= 4

request_id 一致
command_id 一致

RGB 存在

target grounding 合法

RESOLVE disposition = SLOW_READY

通过后：

quality.valid_for_training = true

26. Rejected Sample

失败样本必须保留审计记录，但不能进入监督训练集。

目前支持的 rejection reason 包括：

MODEL_REQUEST_MISSING
MODEL_REQUEST_SCHEMA_VERSION_INVALID
MODEL_REQUEST_REQUEST_ID_MISSING
MODEL_REQUEST_COMMAND_ID_MISSING

MANEUVER_PLAN_MISSING
MANEUVER_PLAN_SCHEMA_VERSION_INVALID
MANEUVER_PLAN_TYPE_INVALID
MANEUVER_PLAN_STEPS_INVALID

RGB_MISSING

REQUEST_ID_MISMATCH
COMMAND_ID_MISMATCH

TARGET_GROUNDING_INVALID

MATCHING_RESOLVE_NOT_FOUND

RESOLVE_NOT_READY:<STATE>

RUNTIME_FAILURE_BEFORE_SUBMIT

NO_CANONICAL_SUBMIT
27. Run-Level Failure

有些 runtime 会在产生 SUBMIT 之前失败。

例如：

unsupported backend
unsupported model profile
runtime initialization failure
service initialization failure

这些 run 不属于 Teacher supervision sample。

但是不能静默消失。

必须写入 rejected JSONL，并：

valid_for_training = false
28. Dataset Version

版本计划：

teacher_distill_v0.1_smoke

目标：

20-50 条真实 Teacher Smoke samples。

下一阶段：

teacher_distill_v0.2

目标：

D1 >= 200 effective Teacher samples。

下一阶段：

teacher_distill_v0.3

目标：

D2 累计 3000-5000 effective Teacher samples。

最终：

teacher_distill_v1.0

D3 Train：

优先达到 8000-15000 effective Teacher samples。

另外独立维护：

Val
Frozen Test
Calibration 300-500
official_like_1000
29. Dataset Update Policy

已经发布的数据版本禁止静默修改。

修正必须产生新版本或 patch version。

必须记录：

parent_version
change_reason
added_sample_ids
removed_sample_ids
builder_git_sha

Frozen Test 一旦冻结不得重新参与数据选择或训练。

30. official_like_1000

official_like_1000 是独立 evaluation-like dataset。

它不是：

Train 的一部分

也不能为了扩大训练数据量直接并入 Train。

31. Anti-Leakage Rules

禁止：

同场景相邻 frame 分别进入 Train / Val / Test

通过修改 sample_id 复制同一 supervision event

重复同一 RGB + ModelRequest + TeacherPlan 来扩大样本数

按照 Teacher target 重新排序 ModelRequest.targets

将失败 Teacher 输出当作正确标签

将缺失 target 错误映射成 no-target

将 JSONL frame 数当作 effective sample 数
32. 当前 Smoke 实例验证

当前已验证真实样本：

scenario_id:
S01_set_speed_20

Teacher:
Qwen/Qwen3.5-2B

Teacher Git SHA:
a05c8b76efcd4c176965223c661f40b153cb1836

ModelRequest:
schema_version = 1.0

ManeuverPlan:
schema_version = 2.0

behavior:
SET_SPEED

target_speed_mps:
5.555555555555555

Teacher target_id:
null

closed-loop:
SUCCEEDED

scenario acceptance:
PASS

当前回归数据治理测试：

accepted = 1
rejected = 2
duplicate sample IDs = 0
dataset validation = PASS

当前已验证 rejection 类型：

MANEUVER_PLAN_MISSING
RESOLVE_NOT_READY:REJECTED
NO_CANONICAL_SUBMIT
33. B1 最终交付目标

B1 最终应提供：

collector.py
build_dataset.py
split_dataset.py
validate_dataset.py

dataset_schema.md

train.jsonl
val.jsonl
test.jsonl
calibration.jsonl
official_like_1000.jsonl

dataset_manifest.json
dataset_quality_report.md

D1 阶段优先交付：

collector.py
dataset_sample_200+
dataset_schema.md
dataset_manifest_v0.json

所有最终有效样本必须可追溯到：

scenario
map
route
seed
frame
Teacher Git SHA
Teacher model
ModelRequest
RGB
ManeuverPlan
closed-loop evidence

<!-- B1_A3_INTERFACE_PATCH_START -->
## B1 -> Student V0 / A3 正式接口映射

从 `smoke_v0.1.1-interface` 起，B1 明确区分两层数据。

### Canonical B1 Dataset
Canonical 数据是 Teacher supervision 的无损治理记录。核心字段保持：

```text
model_request
teacher_plan
visual_input
metadata
sample_class
closed_loop_quality
quality
student_targets
training_policy
```

Canonical 层不得为了某一个训练实现而删除或重命名原始 Teacher 字段。

### A3 Training View
由 `challenge/dataset/build_dataset.py` 从 canonical Train/Val 派生：

```text
canonical model_request -> input
canonical teacher_plan -> teacher.maneuver_plan
canonical sample_class.primary -> metadata.sample_class
canonical dataset_version -> metadata.dataset_version
split assignment -> metadata.split
```

当前正式 A3 view：

```text
training_view/train_a3.jsonl
training_view/val_a3.jsonl
```

### Student V0 target contract
当前 `challenge` 分支的 Student V0 / A3 contract 已固定：

```text
max_steps = 4
max_targets = 8
target_pointer = 0..7
NO_TARGET = 8
```

Canonical 数据仍完整保存 ModelRequest V1 中的 targets，不为 Student V0 静默裁剪原始记录。

如果 Teacher 引用的 target 落在 Student V0 可表达范围之外，则标记 `TARGET_OUTSIDE_TOPK`。该样本不得被静默编码为 `NO_TARGET`，也不得作为普通有效训练样本直接进入 A3。

未来如 A1 正式修改 Student contract，必须生成新的 training-view contract/version；不得静默改变现有 dataset view。

### A3 preflight Gate
当前 Smoke v0 已实际通过 A3 正式 preflight：

```text
Train records: 22
Train valid:   22
Val records:   6
Val valid:     6
Errors:        0
Warnings:      0
A3 preflight:  PASS
```
<!-- B1_A3_INTERFACE_PATCH_END -->
