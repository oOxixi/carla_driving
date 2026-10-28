# 人工标注与复核说明

这是文本语义监督，不是CARLA感知标注、Teacher自生成正确答案或Student蒸馏发布。
当前24条记录均未批准。两位真实复核人必须确认原句与标签，程序不代填批准身份。

## 每条需要确认的内容

1. `steps`按照实际执行先后列出全部肯定任务，允许1至8项，不遗漏恢复速度或返回原车道。
   这不改变现有执行计划最多4个高层步骤的限制；后续需另行做计划编译。
2. `action`使用原有14种动作码。单纯变道是CHANGE_LANE_LEFT/RIGHT；超越/绕障是
   AVOID_OBSTACLE，已经包含需要的变道与通过，不重复记一次变道。
3. `target_text`填写逐字引用的目标描述，不是actor ID。不要把“原车道”“40公里每小时”
   当作待跟随或超越的道路参与者。无法明确指代时保留原文描述并请求确认，不编造身份。
4. `condition`是该动作的先决条件，必须逐字引用原文。A完成后执行B，应把相应条件绑定到B，
   不能单独生成HOLD，也不能把B动作本身作为B的条件。只有“然后/再/最后”的顺序，通常无需另写条件。
5. `speed_kph`单位公里每小时、`gap_m`单位米；只填原句明确提出的数值，未提出就null。
   不把跟车3米理解为车速3，不把条件中“它离开车道”理解为要求本车变道。
6. `direction`是当前动作明确的LEFT/RIGHT/STRAIGHT，没有明确要求则null。
7. `evidence`必须含有支持当前动作的原文，不能只摘录背景或条件。
8. 禁止事项放在`prohibited_actions`中，值为true，不能同时列为肯定执行任务。
9. 文本无法消歧或内部矛盾时`requires_confirmation=true`，不得想象RGB画面补答案。

## 审批记录

记录结构见`record.schema.json`。先填写`label`，由`hashes`命令计算源文本和标签的SHA256。
两位独立复核人各自确认同一原句、同一标签，记录：

- `reviewer_id`：真实、可追溯且不同的复核人标识。
- `approved=true`：真实批准，不是模型“觉得正确”。
- `source_sha256`与`label_sha256`：本次批准的源文本和标签版本。
- `reviewed_at`：真实复核时间，ISO 8601含时区。

负责人确认没有分歧后，才把`annotation_status`设为APPROVED。任何原句/标签变更必须重审。
哈希和两个人名本身不能证明真实复核，需保留团队实际审批记录。不得复制测试代码里的UNIT身份。

## Split与保护集

`group_id`代表同一语义模板/近义改写组，同组不能跨Train和Val。不要为了通过检查把同义句
随意改成不同group_id；工具不能替代人工近重复检查。两侧均应覆盖计划中的语义类别和困难动作。

已有开发题、复核题、提示示例和正式Frozen Test不能成为这批训练/验证材料。
同一条指令训练后再测出的正确，不得记成独立验证收益。当前歧义类样本需要额外认真审核，
不要为追求更高通过率删除、改成简单命令或随意指定看不见的目标。

## 输出标签的格式示意

以下是**格式单元示例**，“停车”属于旧提示保护集，不能复制进这批训练数据：

```json
{
  "steps": [{
    "action": "STOP",
    "target_text": null,
    "direction": null,
    "speed_kph": null,
    "gap_m": null,
    "condition": null,
    "evidence": "停车"
  }],
  "prohibited_actions": {},
  "requires_confirmation": false
}
```

将符合原句的此类对象填入每条记录的`label`，不是要求所有标签都填写STOP。
`origin`必须如实填写来源，未经审核的B1旧Teacher输出、自动生成标签或正式Test数据不能伪装成人工材料。
