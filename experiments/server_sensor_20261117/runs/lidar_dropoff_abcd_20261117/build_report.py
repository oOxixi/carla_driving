import json,pathlib,collections,numpy as np
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/lidar_dropoff_abcd_20261117');rows=json.loads((P/'per_target.json').read_text());audit=json.loads((P/'audit_checks.json').read_text());boxes=json.loads((P/'box_label_audit.json').read_text())['totals'];extra=json.loads((P/'offline_seed_per_target.json').read_text());meta=json.loads((P/'run_metadata.json').read_text());summary={}
for g in 'ABCD':
 r=[z for z in rows if z['group']==g];f=[z for z in r if z['role']=='A'];m=[z for z in r if z['matched_detection']];loc=[z for z in r if z['status']=='LOCATED_UNVALIDATED'];off=[z for z in extra if z['group']==g]
 summary[g]={'frame_samples':len(f),'target_observations':len(r),'matched':len(m),'raw_lidar_avg':float(np.mean([z['raw_lidar_total'] for z in f])),'target_raw_avg':float(np.mean([z['target_raw_semantic'] for z in r])),'target_raw_minmax':[min(z['target_raw_semantic'] for z in r),max(z['target_raw_semantic'] for z in r)],'box_points_avg':float(np.mean([z['box_total'] for z in m])),'nonground_avg':float(np.mean([z['nonground_count'] for z in m])),'largest_component_avg':float(np.mean([z['largest_component'] for z in m])),'largest_component_counts':dict(collections.Counter(z['largest_component'] for z in m)),'valid_cluster_total':sum(z['valid_clusters'] for z in m),'located':len(loc),'failure_reasons':dict(collections.Counter(z['reason'] for z in r)),'box_audit':boxes[g],'selected_target':sum(z['selected_target'] for z in r),'selected_background':sum(z['selected_background'] for z in r),'selected_other_vehicle':sum(z['selected_other_vehicle'] for z in r),'selected_unmatched':sum(z['selected_unmatched'] for z in r),'precision':None,'processing_ms_p50_p95':np.percentile([z['elapsed_ms_per_frame'] for z in f],[50,95]).tolist(),'offline_seed_target_avg':float(np.mean([z['target_raw'] for z in off])),'offline_seed_located':sum(z['status']=='LOCATED_UNVALIDATED' for z in off)}
(P/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
s='''# 32 线远距离 LiDAR 丢点四组对照报告

## 结论

随机丢点在本实验中显著减少目标点，但不是唯一失败原因：关闭随机丢点后平均目标点由 3.15 增到 5.40 个，增幅约 71.6%，方案 C 定位仍为 0/150。关闭两种丢点后，14 个有检测框的目标在现有半径下最大连通分量只有 1 或 2 点，仍没有达到 3 点成簇门槛。表明在本实验固定采样和聚类规则下，点云稀疏与空间连接门槛共同构成瓶颈；不能仅断言是丢点，也不能仅断言只需调聚类。

强度丢点对本批目标没有观测到影响：0.4 与 0 设置下，150 对目标点数逐项相同。D 组目标点实测强度范围为 0.8364～0.8663，均高于阈值 0.8，因此按 CARLA 定义这些目标点没有强度丢点。参数 attenuation=0.004 时，0.8 强度大致对应距 LiDAR 55.79 m；本批目标点距 LiDAR 约 35.87～44.66 m。这仅适用于本次衰减模型与场景，不能推断更远或真实传感器。参考 [CARLA 0.9.16 LiDAR 文档](https://carla.readthedocs.io/en/0.9.16/ref_sensors/#lidar-sensor)。

## 严格控制与样本口径

5 个原始 default_far 场景，每个场景三辆静态车；每场景 10 次连续同步采样。A/B/C/D 四台普通 LiDAR 同时采集，参数分别为 (general, zero)=(0.45,0.4)、(0,0.4)、(0.45,0)、(0,0)，intensity_limit 均为 0.8。所有传感器的实际属性记录在 run_metadata.json；32 线、224000 点/秒、80 m、20 Hz、上下 10°/-30°、0.05 秒仿真步长，传感器安装位姿相同。RGB 和 Radar 使用历史原始保存的同一组检测框和同一份 Radar 回波，在所有四组固定；不是各组重新检测。新的普通/语义 LiDAR 同帧且时间戳相差不超过 1 ms。历史 Radar 时间戳未保存：回放时为满足接口对齐而设置与新帧相同的时间戳，**不能声称历史 Radar 与新采集 LiDAR 真正同帧**；它只用于静态场景下固定其他输入的受控比较。结果不能当作真实时序融合验证。

地图重建后，车辆包围盒投影和历史记录最大偏差小于 0.0001 像素。各组使用未改动的方案 C；Actor 真值和语义 LiDAR 仅在定位之后用于审计。每组 50 个帧样本、150 个车次，其中 10 个车次沿用原场景缺失的检测框；各组分母为全部 150，不是 150 个独立场景。10 次连续采样共享场景和随机序列，不宜按独立场景计算置信区间。
'''
s+='''
## 种子有效性和补充对照

CARLA 0.9.16 中同位置 LiDAR 分别设置 noise_seed=1、2、3 后，连续 8 帧每帧的三份原始点云 SHA-256 完全一致。结合 [0.9.16 源码](https://github.com/carla-simulator/carla/blob/0.9.16/Unreal/CarlaUE4/Plugins/Carla/Source/Carla/Sensor/RayCastLidar.cpp)中种子初始化位置，不能把传入的不同种子当作有效的独立随机种子。正式四组结果因此使用 10 次连续抽样，而不是声称 10 个独立 CARLA 种子；D 组在每个场景的 10 份全扫描 SHA-256 各自完全相同。

为补充种子敏感性，另用 10 个独立的 Python 随机种子对每个场景的 D 组原生回波做离线随机掩码，并按文档中的强度线性规则处理，再输入同一方案 C：A、B、C、D 均为 0/150，目标点均值依次 2.82、5.40、2.82、5.40。这个补充实验不是 CARLA 内部的多种子复现：一般丢点在 CARLA 射线追踪前发生，离线掩码在已命中点上进行，也不是相同 PRNG 实现；不把两种数据混算。

## 四组结果

总点数是每帧全 LiDAR 平均值；目标点数是每个预期车次全云中通过 0.08 m 语义 LiDAR 近邻对应到该 Actor 的平均数量。框内背景数是 140 个有匹配检测的车次中、离线语义对应为背景的点数总和，括号内为语义未匹配点数；不是已经错误分配的点。聚类统计仅对有检测框的 140 个车次。定位率的分母包括未匹配目标。耗时只测方案 C 一次调用，未包含 YOLO 推理、传感器采集和离线真值审计；固定按 A→B→C→D 顺序处理，受机器负载和顺序影响，不能直接作为端到端实时性结论。

| 组 | General / Zero | 全云点/帧均值 | 目标点/车次均值 | 检测框内背景（未匹配） | 最大连通分量均值 | 有效簇总数 | 定位成功 | 点级 Precision | 方案 C 耗时 P50/P95 ms |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
'''
for g in 'ABCD':
 d=summary[g];params={'A':'0.45 / 0.4','B':'0 / 0.4','C':'0.45 / 0','D':'0 / 0'}[g];t=d['processing_ms_p50_p95'];s+=f"| {g} | {params} | {d['raw_lidar_avg']:.1f} | {d['target_raw_avg']:.2f} | {d['box_audit']['background']}（{d['box_audit']['unmatched']}） | {d['largest_component_avg']:.2f} | {d['valid_cluster_total']} | {d['located']}/150 | 无分母 | {t[0]:.1f}/{t[1]:.1f} |\n"
s+='''
四组均没有输出已分配点，因此已分配背景点和其他车辆点均为 0，但点级 Precision 的分母为 0，不能写成 100%。方案 C 的非目标点审计限于可匹配检测框，漏检目标没有候选框。A/C 各有 46 次不足 3 点、94 次无有效簇、10 次检测未匹配；B/D 各有 140 次无有效簇、10 次检测未匹配。

## 逐目标点数与 D 组连接性

下表每行是原始 5 个位置之一的一辆目标车。A 为 10 次原生采样目标点均值；D 为关闭两种丢点的目标点数。最小半径只是使至少 3 个筛选点几何连通的阈值，不保证它们全部属于目标、满足尺寸约束或不会造成串车；最终调整必须做背景和相邻车辆安全对照。`—` 为原始 YOLO 没有该目标的匹配框。

| 原位置/目标 | A 目标点均值 | D 目标点 | D 最大连通分量 | D 当前半径 m | 连通至少 3 点需 m |
|---|---:|---:|---:|---:|---:|
'''
for x in audit['geometry_by_target']:
 def fmt(v):return '—' if v is None else str(v)
 s+=f"| {x['scene']}/{x['role']} | {x['baseline_target_avg']:.1f} | {x['no_drop_target']} | {fmt(x['largest_component'])} | {fmt(x['epsilon_m'])} | {fmt(x['min_epsilon_three_m'])} |\n"
s+='''
## 真值、复核与适用范围

普通 LiDAR 与语义 LiDAR 通过空间最近邻 0.08 m 匹配，不把语义 ID 输入定位；每目标的普通点数量同时与扩展 0.08 m 的 CARLA Actor 包围盒计数对照，600 条车次均相同。抽查 4362 个点，自写匹配器结果与项目原始匹配器一致。真值仍依赖 CARLA，不代表真实车辆测量；包围盒扩展和近邻可能引入误差。输入框内背景存在，但没有被分配的点，无法由本实验评价成功输出的纯度或定位误差。

32 线、上下视场角 40°，相邻竖直线的标称角间隔约 40/31=1.29°；20 Hz、224000 点/秒对应每线每帧约 350 次水平采样，标称水平间隔约 360/350=1.03°。结合本次 36～45 m 范围，角采样间距可达到与当前 0.65～0.80 m 连接半径相近的量级，是观察到孤立点的合理解释；具体射线命中、遮挡及回波位置仍决定真实三维距离。这里把这个解释作为几何分析，不冒充单独改变扫描参数的因果实验。

下一步建议在保持官方规定传感器配置的前提下，优先做单帧聚类距离和点归属的受控对照，并明确报出背景混入、邻车串点、错误定位和成功覆盖；同时可作为独立诊断实验，分别改变点频和视场采样，验证哪一项决定空间间隔。D 仅是诊断上限，不是比赛建议配置。未进行多帧融合。

产物：`per_target.csv/json`（600 条原生逐车记录）、`summary.json`、`audit_checks.json`、`box_label_audit.json`、`seed_probe.json`、`offline_seed_per_target.csv/json`、`run_metadata.json`、实验脚本和 `samples/` 原始数据。全部保存在服务器。
'''
(P/'四组丢点参数验证报告.md').write_text(s,encoding='utf-8');print(s)
