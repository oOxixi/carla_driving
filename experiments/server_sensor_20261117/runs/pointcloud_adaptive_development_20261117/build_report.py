import collections,csv,json,math,pathlib,numpy as np
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_adaptive_development_20261117');final=json.loads((P/'final_frames.json').read_text());v1=json.loads((P/'v1_development_frames.json').read_text());D=json.loads((P/'depth_profile.json').read_text());G=json.loads((P/'geometry_profile.json').read_text());stress=json.loads((P/'synthetic_wide_box_stress.json').read_text());variants=['Baseline','V1','V2','V3','fixed_1.20']
def summarize(z):
 c=collections.Counter();[c.update(x['point_counts']) for x in z];errs=[abs(t['error']) for x in z for t in x['range_errors']];den=c['target']+c['background']+c['other_vehicle'];groups=[g for x in z for g in x['groups']];return {'frames':len(z),'expected':sum(x['expected'] for x in z),'matched':sum(x['matched'] for x in z),'located':sum(x['located'] for x in z),'points':dict(c),'precision':c['target']/den if den else None,'recall_numerator':sum(x['recall_numerator'] for x in z),'recall_denominator':sum(x['recall_denominator'] for x in z),'candidate_multi_vehicle':sum(x.get('candidate_multi_vehicle',0) for x in z),'candidate_target_background':sum(x.get('candidate_target_background',0) for x in z),'candidate_unmatched_semantic':sum(x.get('candidate_unmatched_semantic',0) for x in z),'merged_detection_groups':sum(x['merged_detection_groups'] for x in z),'ambiguity_groups':sum(g['reason'] in ('MULTIPLE_PLAUSIBLE_CLUSTERS','GEOMETRY_REJECTED_OR_AMBIGUOUS') for g in groups),'group_count':len(groups),'error_count':len(errs),'abs_error_p50_p95_max':np.percentile(errs,[50,95,100]).tolist() if errs else None,'latency_p50_p95_max_ms':np.percentile([x['elapsed_ms'] for x in z],[50,95,100]).tolist() if z else None,'reasons':dict(collections.Counter(g['reason'] for g in groups))}
summary={ds:{v:summarize([z for z in final if z['dataset']==ds and z['variant']==v]) for v in variants} for ds in ('dev','oldA','holdout')};scans={ds:{v:summarize([z for z in v1 if z['dataset']==ds and z['variant']==v]) for v in ('R0','alpha_1.1','alpha_1.2','alpha_1.3','alpha_1.4','alpha_1.5','fixed_1.20')} for ds in ('dev','oldA')}
summaryfile={'final':summary,'alpha_scans':scans,'stress_frames':stress['frames'],'stress_by_variant':{v:{'selected':sum(x['status']=='LOCATED_UNVALIDATED' for x in stress['rows'] if x['variant']==v),'selected_multi':sum(x['selected_cross_vehicle'] for x in stress['rows'] if x['variant']==v),'selected_background':sum(x['selected_background'] for x in stress['rows'] if x['variant']==v),'geometry_rejections':sum(x['reason']=='GEOMETRY_REJECTED_OR_AMBIGUOUS' for x in stress['rows'] if x['variant']==v)} for v in variants},'interpretation':'Offline prototype; no production deployment; independent validation is too small and negative examples insufficient.'};(P/'summary.json').write_text(json.dumps(summaryfile,ensure_ascii=False,indent=2)+'\n')
with (P/'frame_metrics.csv').open('w',encoding='utf-8-sig',newline='') as f:
 keys=['dataset','case','frame','radar_sync','variant','expected','matched','located','recall_numerator','recall_denominator','merged_detection_groups','candidate_multi_vehicle','candidate_target_background','candidate_unmatched_semantic','elapsed_ms'];w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(final)
with (P/'target_group_metrics.csv').open('w',encoding='utf-8-sig',newline='') as f:
 keys=['dataset','case','frame','variant','group_id','role','status','reason','diagnostic_outcome','box_count','nonground_count','selected_count','selected_target','selected_background','selected_other_vehicle','selected_unmatched_semantic','epsilon_m','depth_limit_m'];w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();
 for row in final:
  for g in row['groups']:w.writerow({**row,**g})
fmt=lambda x: '—' if x is None else f'{x:.3f}'
s='''# 距离自适应聚类、深度约束和几何检查实验报告

## 决策

按要求开发了独立实验版本 Baseline、V1、V2、V3，并完成留出位置验证；**目前没有达到接入生产代码的证据要求**。V1 有覆盖提升；V2 的实验深度阈值在历史 A 组明显减少有效车辆点；V3 的几何阈值缺少反例标定，压力测试中对单辆车纯净点簇也发生拒绝。所有阈值都只作离线诊断，未修改生产代码。

## 数据与隔离

新采集 48 帧、48 个预定主目标位置：24 帧调试，24 帧初定验证；对车辆中心做跨集合空间核对后，排除 3 个距训练车辆过近的验证场景，最终验证为 21 帧、35 个预期车次。验证集与调试集及历史 A 组所有目标中心最小间距约 11.93 m；这种划分可排除同一位置重复帧，但仍同一 CARLA 地图，不能等同不同城市或真实道路的独立性。另保留历史 A 组 50 帧、150 车次供参考；10 帧是连续采样，不是独立随机种子。

新数据使用普通 LiDAR 32 线、224000 点/秒、默认丢点参数；相机、LiDAR、语义 LiDAR、Radar 均记录真实帧号与时间戳，48/48 帧传感器同步差不超过 1 ms。车型为轿车、SUV、卡车，采集位置约 17～55 m，包含正后方与倾斜角、相邻车和遮挡组合，以及晴天、夜间、雨和雾。CARLA 的雨雾只代表天气/视觉变化，未证明或设置真实 LiDAR/Radar 雨雾退化。场景为同一 Town05，不能宣称覆盖实车护栏和建筑的所有情况。

每个版本使用相同保存的图像检测框、LiDAR、Radar。新数据使用真正同帧 Radar，仅保留原方案 C 对候选簇的 Radar 支持；新增深度差判据只使用 LiDAR。历史 A 组沿用旧 Radar 回波及占位时间戳，不能视为实时同步验证。语义 LiDAR/Actor 真值仅用于离线标定和事后核对，不输入定位函数。

## 各版本定义

- Baseline：原 R0 + 方案 C；保留分组、唯一归属和原有物理尺寸上限。
- V1：仅在最终成簇处使用 `clip(1.5 × R0, 0.38m, 1.20m)`；1.5 根据调试集选择，并在独立验证前锁定。单检测框锚点的原聚类、检测框分组和重叠点归属保持原样。固定 1.20 m 只作对照。
- V2：在 V1 上增加 LiDAR 三维径向距离差门限。各距离段门限来自调试集同车点对的 95 分位，点对不足 10 个的距离段使用合并数据回退；这不是已经证明安全的阈值。
- V3：在 V2 上增加点簇径向范围检查，调试集同车候选簇最大范围加 0.08m 作为探索性阈值。保留原纵向/横向/垂向范围和至少 3 点检查，拒绝的候选簇导致 UNKNOWN/AMBIGUOUS，不强制选择另一个。该范围不是已验证的车辆物理尺寸阈值，尤其可能过严限制卡车。

输出区分 `CANDIDATE_UNVALIDATED`（候选未验真）、`AMBIGUOUS`、`FAILED`；候选点簇不代表完整车辆中心或占据范围。检测框内点的一致性由输入筛选保证，不能把它当作独立的视觉验证。

## V1 补偿系数调试

每组调试集 39 个预期车次，其中 22 个有匹配检测框。点级 Recall 的分母是匹配框内能对应目标的 LiDAR 点；漏检车次仍计入覆盖率分母，但不在条件 Recall 分母。选中点中没有未匹配语义点。95 分位误差只在各版本成功样本上计算，各版本样本不同。

| 半径策略 | 定位/39 | 已选目标点/错误背景/其他车 | 点级 Recall | 歧义组/全部组 | 表面距离误差 P95/最大 m |
|---|---:|---|---:|---:|---|
'''
for v in ['R0','alpha_1.1','alpha_1.2','alpha_1.3','alpha_1.4','alpha_1.5','fixed_1.20']:
 a=scans['dev'][v];c=a['points'];e=a['abs_error_p50_p95_max'];s+=f"| {v} | {a['located']} | {c.get('target',0)}/{c.get('background',0)}/{c.get('other_vehicle',0)} | {a['recall_numerator']}/{a['recall_denominator']} | {a['ambiguity_groups']}/{a['group_count']} | {fmt(e[1] if e else None)} / {fmt(e[2] if e else None)} |\n"
s+='''
1.5 的选择规则：在新调试集上先要求已评分 Precision ≥99% 且没有已匹配不同车辆被分为同一组，再优先定位覆盖、其次条件点 Recall；1.4 与 1.5 均定位 12/39，1.5 的目标点 Recall 较高。这个规则只用于选择实验参数，不代表验收达标。每个 α 和固定 1.20 m 的候选簇，在该调试集及历史 A 数据中均没有观测到已标注双车或目标加背景混簇；但这两批数据没有足够可检验的负样本。

## 四版本独立验证结果

21 帧有 35 个预期车次，仅 10 个有匹配 YOLO 框，另外 25 个无法由聚类恢复。定位是 `LOCATED_UNVALIDATED`，不是可信定位认证；Precision 仅统计选中、且语义能够评分的点。误差 P95 和最大值仅基于成功结果，Baseline 只有 1 个，不能作为可靠分布基准。耗时为单帧方案 C 调用，运行顺序随机化，不含相机检测、传感器采集和离线审计。

| 版本 | 定位/35 | 目标/背景/邻车/未评分选中点 | Precision | 条件 Recall | 歧义组/全部组 | 误差 P95/最大 m | 处理耗时 P50/P95/最大 ms |
|---|---:|---|---:|---:|---:|---|---|
'''
for v in variants:
 a=summary['holdout'][v];c=a['points'];e=a['abs_error_p50_p95_max'];t=a['latency_p50_p95_max_ms'];un=c.get('unmatched_semantic',0)+c.get('unmatched_detection',0);precision='—' if a['precision'] is None else f"{a['precision']*100:.1f}%";s+=f"| {v} | {a['located']} | {c.get('target',0)}/{c.get('background',0)}/{c.get('other_vehicle',0)}/{un} | {precision} | {a['recall_numerator']}/{a['recall_denominator']} | {a['ambiguity_groups']}/{a['group_count']} | {fmt(e[1] if e else None)} / {fmt(e[2] if e else None)} | {t[0]:.2f}/{t[1]:.2f}/{t[2]:.2f} |\n"
s+='''
四组候选簇均没有观察到已标注的双车混簇或目标加背景混簇，未评分候选簇也为 0；但实际有检测的车次太少，不能据此声称跨车错误概率为零或达到 99% 精度的泛化要求。用户未指定绝对实时预算与误差门槛，因此只与 Baseline 比较，不自行判定达标。

## 深度与几何约束的直接影响

调试集中，V1/V2/V3 均定位 12/39，但条件 Recall 依次为 79/161、75/161、75/161；V2 减少了 4 个有效目标点，未观察到背景点减少。历史 A 组 V1→V2 的定位数由 48/150 降到 15/150，目标点 Recall 由 178/418 降到 48/418；这批数据的 Radar 属历史回放，仅作为该 LiDAR 门限在稀疏点云下的警示，不当作真实同步实验。

深度门限标定所用新调试数据有 104 对同车点，但在候选连接范围内 **0 对目标与背景/其他车的负样本**。所以它只描述同车点差异，无法确定对背景分离是否有效。V3 几何限度仅由 14 个纯净候选簇估计，35 m 以上各距离段样本不足而使用总体回退；它不能作为普适车辆物理上限。自然验证集中 V3 未新增任何几何拒绝，无法证明几何检查有效。

额外构造了 36 帧**人工过宽检测框压力测试**：把真实传感器帧中两辆车的原 YOLO 框合并成一个人工框，模拟检测器错误；它不属于自然 YOLO 评测。四版本未形成已标注的双车混簇，但 V1 仍有 29/36 帧输出了单车候选；由于人为输入框同时包住两车，不能把选择一辆车当成正确关联。V3 在其中 3 帧触发几何拒绝，而对应 V2 被选中点各自只属于一辆车、没有已核对的背景点：提示当前阈值可能过严，也不证明此前选择就是正确目标。此压力数据不能替代真实紧邻车辆和护栏的负样本。

## 完成的复核与后续

原始 R0 在 95 个输入上逐字段、点状态和所有权与正式实现一致；所有 475 次最终对照都验证了聚类前分组与候选点不变，且每个 ASSIGNED 点只有唯一 owner。单元检查覆盖原连通分量等价、人工两深度层可分离、几何拒绝后保持 UNKNOWN 且不分配点。实验没有多帧融合，也没有做 Radar 消融。

下一步先补采真实的目标邻近护栏/背景、紧邻车辆和遮挡负样本；从独立训练场景评估正负深度差重叠，重新设计物理宽松的车辆尺寸/深度范围，避免凭当前少量同车数据固化阈值。扩大独立地图、车型、距离和足够 YOLO 命中的验证集后，才有条件讨论是否达到 99% 精度和 0 次跨车错误，再与 Baseline 对比延迟及误差。不得将 1.5、深度阈值或 V3 当前阈值当成最终生产参数。

主要文件：`experimental_group_localization.py` 独立实现；`collect_independent.py` 新采集脚本；`v1_parameter_lock.json`、`depth_profile.json`、`geometry_profile.json` 为实验参数与选择依据；`final_frames.json`、`frame_metrics.csv`、`target_group_metrics.csv`、`summary.json` 为结果；`synthetic_wide_box_stress.json` 为人工压力测试；`test_invariants.json` 为复核结果。原始传感器帧及同步时间戳保存在 `new_scenes/`。
'''
(P/'自适应聚类分阶段验证报告.md').write_text(s,encoding='utf-8');print('REPORT OK',len(s))
