import collections,json,pathlib,numpy as np
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/radius_sweep_ad_20261117');rows=json.loads((P/'per_target.json').read_text());controls=json.loads((P/'overlap_control_rows.json').read_text());frames=json.loads((P/'overlap_control_frames.json').read_text());metadata=json.loads((P/'metadata.json').read_text());R=['R0','R1','R2','R3','R4','R5'];summ={}
for src in 'DA':
 summ[src]={}
 for k in R:
  z=[x for x in rows if x['source']==src and x['radius']==k];m=[x for x in z if x['matched_detection']];selected=[x for x in z if x['status']=='LOCATED_UNVALIDATED'];errors=[abs(x['range_error_m']) for x in selected];pts={key:sum(x[key] for x in z) for key in ('selected_target','selected_background','selected_other_vehicle','selected_unmatched')};den=pts['selected_target']+pts['selected_background']+pts['selected_other_vehicle'];summ[src][k]={'vehicles':len(z),'matched':len(m),'candidate_at_least_3':sum(x['candidate_count']>0 for x in m),'located':len(selected),'pure_selected':sum(x.get('selected_pure',False) for x in selected),'selected_points':pts,'precision_scored':pts['selected_target']/den if den else None,'candidate_target_background':sum(x['candidate_mixed_background'] for x in m),'candidate_multi_vehicle':sum(x['candidate_multi_vehicle'] for x in m),'abs_range_error_p50_p95_max':np.percentile(errors,[50,95,100]).tolist() if errors else None,'reasons':dict(collections.Counter(x['reason'] for x in z))}
check={}
for k in R:
 z=[x for x in controls if x['radius']==k];f=[x for x in frames if x['radius']==k];errs=[abs(x['range_error_m']) for x in z if x['range_error_m'] is not None];check[k]={'frames':len(f),'expected':sum(x['expected'] for x in f),'located':sum(x['located'] for x in f),'selected_target':sum(x['target'] for x in z),'selected_background':sum(x['background'] for x in z),'selected_other_vehicle':sum(x['other_vehicle'] for x in z),'unmatched_semantic':sum(x['unmatched_semantic'] for x in z),'unmatched_detection':sum(x['unmatched_detection'] for x in z),'candidate_multi_vehicle':sum(x['candidate_multi_vehicle'] for x in z),'candidate_target_background':sum(x['candidate_target_plus_background'] for x in z),'abs_range_error_p50_p95_max':np.percentile(errs,[50,95,100]).tolist() if errs else None}
index={(x['frame'],x['role'],x['radius']):x for x in controls};assert len(index)==len(controls);paired={}
for k in R[1:]:
 pairs=[(x,index[x['frame'],x['role'],k]) for x in controls if x['radius']=='R0' and x['role'] is not None and x['range_error_m'] is not None and index[x['frame'],x['role'],k]['range_error_m'] is not None];d=[abs(y['range_error_m'])-abs(x['range_error_m']) for x,y in pairs];paired[k]={'n':len(pairs),'absolute_error_increased':sum(v>1e-6 for v in d),'absolute_error_decreased':sum(v< -1e-6 for v in d),'max_increase_m':max(d,default=0)}
result={'far':summ,'overlap_controls':check,'overlap_paired_comparison_to_R0':paired};(P/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
s='''# A、D 组聚类半径扫描与邻车对照

## 实验范围

按用户要求先读取已保存 D 组，再读取 A 组；每组 5 个原始位置、各 10 次采样，均为 150 个车次，其中 10 次沿用原先缺失的检测框。D 组每个位置的 10 帧点云完全相同，故应同时看独立目标数，不可视为 150 个独立场景。A 组 10 次连续采样也并非独立随机种子。D 是关闭丢点后的诊断上限，不是比赛传感器设置。新采集 LiDAR 为同步帧，Radar 沿用历史录制并对齐占位时间戳，不是新帧实测 Radar。5 个位置均是静态、单路段的同一车型。

R0 为原始距离自适应半径；R1～R5 的 0.75、0.85、0.95、1.05、1.20 m 仅作为离线探索常数。只在实验进程内覆盖方案 C **最后形成连通分量**时使用的半径；检测框分组、单框锚点、重叠点归属、地面和高度过滤、簇选择及 Radar 规则均不变。100 帧 R0 的分组、筛选点、最终状态、候选簇与上次保存结果完全一致；另外 500 次比较验证候选点等前置结果未变。没有改动生产代码或传感器，也未使用多帧融合。

语义 LiDAR 0.08m 近邻和 Actor 标注只用于离线核对。定位为算法返回 LOCATED_UNVALIDATED，并非安全认证；纯度只对有语义真值的已选择点计算，未知数单列。误差为最近被选择 LiDAR 点到自车原点的水平距离减去自车原点到 Actor 包围盒最近水平表面的距离；并不是车辆中心误差。

## 六个半径的结果

表中定位分母包含未匹配检测的 10 个车次，成簇为检测框内至少形成一个 3 点以上连通分量的车次数。P95/最大误差只针对本半径下成功输出的目标，成功集合会改变，不能直接作同目标误差增减结论。

| 数据 | 半径 | 成簇/150 | 定位/150 | 选中点：目标/背景/邻车/未匹配 | 点级 Precision | 距离绝对误差 P95/最大 m |
|---|---|---:|---:|---|---:|---|
'''
for src in 'DA':
 for k in R:
  x=summ[src][k];v=x['selected_points'];prec='—' if x['precision_scored'] is None else f"{100*x['precision_scored']:.1f}%";e=x['abs_range_error_p50_p95_max'];err='—' if e is None else f'{e[1]:.3f} / {e[2]:.3f}';val='原始自适应' if k=='R0' else f'{metadata["radius_values"][k]:.2f} m';s+=f"| {src} | {k} {val} | {x['candidate_at_least_3']} | {x['located']} | {v['selected_target']}/{v['selected_background']}/{v['selected_other_vehicle']}/{v['selected_unmatched']} | {prec} | {err} |\n"
s+='''
D 组 10 次重复输入相同，R5 的 140/150 实际为 **14/15 个不同位置/角色**；缺失的 1 个没有匹配检测框。A 组 R5 剩余 82 次：46 次不足 3 点，26 次没有有效簇，10 次检测未匹配。纯度的 100% 仅是被选中且可评分的点，不能扩大为所有点或其他场景的正确性。

值得注意：D 组 R2 产生 110 次定位，但 R3 只有 90 次；R3 的 20 次产生多个相近候选簇，原有保守规则拒绝选择，故半径和定位数不保证单调。A 组 R3 有 3 次距离绝对误差约 0.693 m，尽管选中点均来自目标；这表明点纯度高不自动意味着测距准确。R0 本来没有任何成功样本，不能比较其距离误差。对于同时在 R1 和 R5 成功的远距离同一目标样本，A 组 13 对、D 组 80 对的最近表面距离误差均未增加或减少；但这不能代表 R5 新恢复目标的误差。

## 逐目标定位数

每格表示 10 次采样中返回定位的次数；D 的 10 次是重复相同点云。原始位置 4/C 的检测框缺失，所有半径均无法定位。

| 原始位置/角色 | A R0/R1/R2/R3/R4/R5 | D R0/R1/R2/R3/R4/R5 |
|---|---|---|
'''
for scene in range(5):
 for role in 'ABC':
  vals=[]
  for src in 'AD':vals.append('/'.join(str(sum(x['status']=='LOCATED_UNVALIDATED' for x in rows if x['source']==src and x['scene']==scene and x['role']==role and x['radius']==k)) for k in R))
  s+=f'| {scene}/{role} | {vals[0]} | {vals[1]} |\n'
s+='''
## 重叠和邻车补充对照

补充回放 54 帧既有相邻、遮挡和重叠数据，包含 5 帧人工注入重复框；36 帧两辆预期车都有匹配检测。每个半径都保持分组和聚类前的点不变，使用与上面相同的单帧算法。候选簇中未发现同时含两个已标注测试车辆的簇，也未发现目标与背景混合的候选簇；但其中检测漏检、遮挡和近邻关联有局限，不能作为一般安全保证。

| 半径 | 预期车次定位 | 被选点：目标/背景/其他测试车/未评分 | 最近表面距离误差 P95/最大 m |
|---|---:|---|---|
'''
for k in R:
 x=check[k];e=x['abs_range_error_p50_p95_max'];un=x['unmatched_semantic']+x['unmatched_detection'];s+=f"| {k} | {x['located']}/{x['expected']} | {x['selected_target']}/{x['selected_background']}/{x['selected_other_vehicle']}/{un} | {e[1]:.3f} / {e[2]:.3f} |\n"
s+='''
R1 的误差 P95 比 R0 大，但两个统计使用的成功目标不相同。只比较 R0 和 R1 均成功的 64 个相同目标，绝对误差没有增加，6 个减少；较大的 P95 来自成功集合变化，不能说是同目标误差变大。R0～R5 在此数据中未选中经语义核对的背景或其他测试车点；未证明极端密集交通、所有障碍物或真实传感器条件下不会误合并。

## 决策

结果支持进一步研究距离自适应连接半径，但不足以从这些数据确定可部署的 ε0、k 和上下限：远距离部分只有 5 个静态位置，R1～R5 是固定半径测试，且 A 组即使 1.20m 仍有 46 次连 3 个输入点都不足。不能以 D 组 14/15 或局部 100% 纯度作为比赛条件下的最终效果。下一步应在原始传感器配置下使用相互独立的多距离、多车型、真实重叠及背景场景，拟合并留出验证集，验证距离规则、深度和几何约束与误报/漏报，再决定是否修改生产代码。

文件：`per_target.csv/json` 含 1800 条逐车半径记录，JSON 还保存每个 3 点以上候选分量的点编号、目标/背景/邻车及未评分点数；`summary.json` 为汇总；`overlap_control_rows.csv/json`、`overlap_control_frames.json` 为补充对照；两个独立脚本和 `metadata.json` 保存复现依据。所有文件都在服务器。
'''
(P/'聚类半径扫描报告.md').write_text(s,encoding='utf-8');print(s)
