# B1 D3 Wave2核查记录

上级：[数据治理](../modules/challenge-data.md)、[场景执行](../modules/vehicle-scenarios.md)。日期2026-09-20，基线fe1ba839。业务问题未修复。

| ID | 已证实 | 待证/下一步 |
|---|---|---|
| W2-01 | A01 base FOLLOW、GEN KEEP_LANE；4f286d29原始不一致→9a4747d2生成→54e13bc6只修base | 9/9实际失败与唯一因果需原始run及同seed对照 |
| W2-02 | CX02两个GEN旧命令；base改FOLLOW/最近同车道文本及actor | 核对完整差异后probe |
| W2-03 | 当前STOP构造不带target，runner已有alias链 | 历史8/8实际版本、是否另有感知失败 |
| W2-04 | 19 GEN中9个存在语义字段差异 | 确认是否有意独立契约后再修 |
| W2-05 | WATCHDOG_ALERT有多种来源 | long首次runtime_alerts与告警前帧 |
| W2-06 | 当前可见仓库未找到对应Wave2原始审计/selection | 727/273及family通过率/gates为成员报告，未独立验证 |

## 差异实例

根目录：[generalization](../../../scenarios/generalization)。比较commands、expected、qwen_expected、oracle、proposed_acceptance，不将合法几何扰动误报。

| family | member2目录与GEN编号 | 差异字段 |
|---|---|---|
| ACC_A01_lead_brake | variant/000、unseen/001 | commands |
| CX02_multi_vehicle_target_follow_brake | variant/000、unseen/001 | commands；另有actor变更 |
| OFFICIAL_S2_COMPLEX_AVOIDANCE_8KM | variant/000、unseen/001 | commands/qwen_expected/oracle/proposed_acceptance |
| OFFICIAL_S3_EXTREME_EMERGENCY_6KM | unseen/000、variant/002 | commands/proposed_acceptance |
| OFFICIAL_S3_EXTREME_EMERGENCY_6KM | variant/001 | commands/qwen_expected/oracle/proposed_acceptance |

A03/A04/A06/CX01上述字段未发现同类差异，不代表闭环通过。

## 数据口径与证据

[D2 manifest](../../../challenge/dataset/releases/d2_v1_1/release_manifest.json)：3592，Train2513/Val539/Reserved540，另隔离8。
[Wave1治理](../../../challenge/dataset/releases/d3_wave1_addon_v1/governance_report.json)：2000runs，2398原始候选=2055正样本+308HN+35隔离；非隔离2363。Train add1747、Val add308。新增scenario_id/source_text均0，独立场景/模板验证不可用。

重分组不能消除历史训练/调参暴露；family+map+route+seed组合不保证family-disjoint。新版本另定义holdout，保留D2冻结记录。

闭合运行根因需要selection及哈希、实际collector/runner/Teacher SHA、启动参数/输出目录、逐run summary/stdout；A04关联request/plan/alias，A03读failed_keys，long读首次runtime_alerts。未持久化字段记可观测性缺口，不假装已有。

定位链：[来源](scenario-lineage.md)→[target](target-grounding.md)/[验收](acceptance-diagnosis.md)/[watchdog](watchdog-diagnosis.md)。
