import collections,csv,html,json,pathlib,numpy as np
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/yolo_unmatched25_diagnosis_20261117');d=json.loads((P/'diagnosis.json').read_text());vis=json.loads((P/'visible_mask_audit.json').read_text())['rows'];vis={(x['case'],x['role']):x for x in vis};audit=json.loads((P/'recall_audit.json').read_text());rows=[]
for x in d['rows']:
 a=vis[(x['case'],x['role'])];raw=x['best_pre_nms_vehicle_iou30'];wrong=x['best_pre_nms_any_class_iou30'];final=a['best_final_mask_support'];fcover=final['target']['target_pixel_coverage'] if final else None;other=max((v['target_pixel_coverage'] or 0 for v in final['others'].values()),default=0) if final else 0
 if x['class_category'].startswith('正式车框') and fcover is not None and fcover>=.5 and other>=.5:category='一个正式框同时覆盖两车，关联歧义'
 elif x['class_category'].startswith('正式车框'):category='附近正式框主要覆盖另一车；目标未独立检出'
 elif raw:category='车辆候选低于0.35，未进入正式输出'
 elif wrong:category=f"无车辆类候选；低分{wrong['class']}候选"
 else:category='无IoU≥0.30的车辆类候选'
 rec={'case':x['case'],'frame':x['frame'],'role':x['role'],'vehicle_model':x['vehicle_model'],'weather':x['weather'],'scene_type':x['scene_type'],'center_distance_m':round(x['distance_center_m'],2),'box_width_px':round(x['gt_box_width_px'],1),'box_height_px':round(x['gt_box_height_px'],1),'best_raw_vehicle_conf':round(raw['confidence'],4) if raw else None,'best_raw_vehicle_class':raw['class'] if raw else None,'best_raw_vehicle_iou':round(raw['iou'],3) if raw else None,'best_other_class':wrong['class'] if not raw and wrong else None,'best_other_conf':round(wrong['confidence'],4) if not raw and wrong else None,'best_final_box_iou':round(x['best_final_vehicle_iou']['iou'],3) if x['best_final_vehicle_iou'] else None,'final_box_mask_coverage':round(fcover,3) if fcover is not None else None,'final_box_other_vehicle_coverage':round(other,3) if final else None,'reconstructed_visible_pixels':a['visible_pixels_reconstructed'],'visible_ratio_vs_solo':round(a['visible_fraction_vs_without_other_vehicles'],3) if a['visible_fraction_vs_without_other_vehicles'] is not None else None,'reason':category,'annotation_file':f"annotated/{x['case']}_{x['role']}.png"};rows.append(rec)
assert len(rows)==25 and audit['expected']==35 and audit['strict_original_full_3d_projected_box_matched']==10 and audit['visible_bbox_iou30_one_to_one_matches']==10
with (P/'逐目标诊断.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
s='''# 25 个未匹配目标：YOLO 与框匹配诊断

## 结论

在原始 21 帧、35 个目标中，原 YOLO 最终输出 10 个车辆类框。按原来的 3D Actor 完整包围盒投影、IoU≥0.30 和一对一贪心匹配，10 个框全部匹配到不同目标：**目标匹配率 10/35＝28.6%，已输出车辆框的匹配率 10/10＝100%**。后者以输出框为分母，不代表 100% 的车辆被检出。

原始帧未保存实例分割，因此在独立 CARLA 进程中按原车辆、位置、朝向、天气和相机重建 21 帧，并使用实例分割生成可见像素边界框；按重建可见框 IoU≥0.30、一对一匹配，仍为 **10/35＝28.6%**，匹配到的也是同一批目标。可将此作为第二种可见目标框口径下的检测召回估计，但它仍依赖匹配条件及重建，不是人工标注的无条件真实召回率。重建不是原始图：重建 RGB 与原图全图平均绝对差 0.003～4.517/255，Actor 3D 框投影坐标一致；因此只能作为补充证据。

25 个未匹配目标中：22 个有与完整真值投影框 IoU≥0.30、最高类为 car/bus/truck 的原始候选，但分数均小于原阈值 0.35（约 0.0017～0.3483）；这些候选在重建可见像素上的覆盖至少 77%，支持它们与目标空间相符，但极低分候选不能当成可靠识别。另 3 个没有上述车辆类候选，其中一个有 IoU 0.811、分数 0.153 的 person 候选，提示类别混淆但同样未达到正式阈值。没有发现 IoU≥0.30 且分数≥0.35 的未匹配车辆候选，也没有发现达到阈值的非车辆类别候选；因此这 25 个没有证据表明是该口径下 NMS 或类别过滤误删了高分目标框。

有 4 个未匹配目标与正式车辆框存在较明显二维重叠：其中两个框在重建实例分割中同时覆盖两辆车，属于单框多目标的歧义；另外两个框主要覆盖另一辆车，不能把它们算作本目标已检出。重建显示 6/25 的目标在另一测试车存在时的可见像素比单独放置时减少超过 1%，最低约 66.7%；此比值只评估其他测试车辆带来的遮挡，不能排除道路设施遮挡，也不等于原图中的精确遮挡率。

## 25 个目标逐项表

距离是自车原点至目标 Actor 包围盒中心的水平距离。尺寸为原记录的完整 3D 包围盒投影宽高，可能大于真正可见部分。`候选`是原始网络中最高类别为车辆、且与完整投影框 IoU≥0.30 的最高分候选，格式为 `类别/分数/IoU`；这不是正式检测框。`可见比`为重建时“全部测试车辆存在”与“只保留目标车辆”的实例像素数之比。`—`表示该项不存在。图中红框是完整 Actor 投影、绿框是原正式检测、黄框是最高低分候选；均保存在服务器。

| 目标 | 距离 m | 天气 | 投影宽×高 px | 最高车辆候选 | 可见比 | 证据判断 |
|---|---:|---|---|---|---:|---|
'''
for x in rows:
 candidate=f"{x['best_raw_vehicle_class']}/{x['best_raw_vehicle_conf']:.4f}/{x['best_raw_vehicle_iou']:.3f}" if x['best_raw_vehicle_conf'] is not None else '—';ratio=f"{x['visible_ratio_vs_solo']:.2f}" if x['visible_ratio_vs_solo'] is not None else '—';s+=f"| [{x['case']}/{x['role']}]({x['annotation_file']}) | {x['center_distance_m']:.1f} | {x['weather']} | {x['box_width_px']:.1f}×{x['box_height_px']:.1f} | {candidate} | {ratio} | {x['reason']} |\n"
s+='''
## 两个共享框与另外两个重叠框

- `holdout_extra_250_39/N`：原输出为 truck 0.409，原完整投影 IoU 0.196；其检测框在重建分割图中覆盖该目标约 67.2% 的可见像素，同时覆盖另一辆车约 100%。这是一框覆盖两车的歧义，不是可靠的两辆车分别检出。
- `holdout_extra_250_55/N`：原输出为 car 0.369，IoU 0.217；该框覆盖目标约 98.3% 可见像素，也覆盖另一辆车约 100%，同样不能一框匹配两辆车。
- `holdout_257_30/T`：现有正式框覆盖该目标约 12.7% 可见像素、另一车约 94.2%，主要是另一辆车；重建时该目标相对单车可见像素约 66.7%。
- `holdout_extra_250_25/T`：正式框覆盖该目标约 2.8% 可见像素、另一车约 98.3%，主要是另一辆车；目标另有低于阈值的 truck 候选 0.303。

如果只以“有任意车辆框覆盖目标 ≥50% 的重建可见像素”计算，不要求一框只能对应一个目标，可得到 12/35；多出的正是前面两个共享框目标。这只是像素覆盖的宽松观察值，**不是 12 个独立 YOLO 检出，也不是标准召回率**。

## 边界与建议

模型回放采用相同 ONNX 权重、640×640 输入、置信度 0.35、类内 NMS IoU 0.45，与采集当时记录的 21 帧输出逐帧一致；没有修改生产阈值、模型或匹配规则。22 个低分候选中有 18 个分数低于 0.30，仅 4 个在 0.30～0.35；置信度不是经过本场景标定的正确率，不能只依据这份表直接降低阈值。输出框的评分与候选 IoU 仅是统计和定位线索。

这些目标距自车中心约 18.0～52.1 m，完整投影宽度 14.1～76.2 px；其中 11 个宽度不足 25 px。小尺寸、车身侧向角、遮挡、夜间/雨雾视觉变化均可能影响检测，但场景数量少且因素交织，不能证明某一个因素是根因。6 个受到其他测试车辆遮挡不等于其余 19 个无环境遮挡。需继续核对目标的实际可见形态，以及更多不同场景的误检情况。

下一步建议保持阈值不变，先针对小目标、不同车型和光照检查候选分数与误检；对双车共框案例检查模型是否产生分离实例及框的归属，不能靠一对一匹配算法把同一个框强行分给两辆车。只有建立独立标注集、同时量化召回和误报之后，才评估检测策略或阈值调整。方案 C 的重复框分组解决的是同一目标多框，不会凭空把一框覆盖的两辆车拆成两个可靠检测。

结果文件：`逐目标诊断.csv`、`diagnosis.json`（包含完整候选和坐标）、`recall_audit.json`、`visible_mask_audit.json`、`visibility_cases/`、`annotated/`、可复现脚本和 `浏览25目标.html`。本报告的分类由原始输出、投影与重建实例分割进行自动审计；未对 25 张原图进行人工视觉标注，仍建议结合注释图逐张复核。
'''
(P/'25目标未匹配诊断报告.md').write_text(s,encoding='utf-8')
page=['<!doctype html><meta charset="utf-8"><title>25个目标检测诊断</title><style>body{font:15px sans-serif;background:#f5f7fa;color:#17212a;max-width:1200px;margin:auto}section{background:white;border:1px solid #ccd5dd;margin:12px 0;padding:14px;border-radius:8px}img{max-width:800px;width:100%}p{line-height:1.5}</style><h1>25个未匹配目标：原图叠加框</h1><p>红：完整Actor投影；绿：正式YOLO框；黄：低分候选。低分框不是正式输出。可见比来自重建场景，不是原帧实例标注。</p>']
for x in rows:
 text=html.escape(f"{x['case']}/{x['role']} 距离 {x['center_distance_m']}m | {x['weather']} | {x['reason']} | 低分候选 {x['best_raw_vehicle_conf']} | 可见比 {x['visible_ratio_vs_solo']}");page.append(f'<section><h2>{text}</h2><img src="{html.escape(x["annotation_file"])}" alt="标注图"></section>')
(P/'浏览25目标.html').write_text('\n'.join(page),encoding='utf-8');print('REPORT',len(rows),'rows',dict(collections.Counter(x['reason'] for x in rows)))
