"""Summarize real runs; CARLA actor boxes used only after control for evaluation."""
import json,glob,math
from pathlib import Path
import numpy as np
BASE=Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/lora_compare_20261116')
results={}
for case in ('40m','60m','occlusion'):
 expected='occluder_near' if case=='occlusion' else 'lead_target'
 for model in ('base','v14'):
  name=f'{case}_{model}';p=BASE/name;logs=glob.glob(str(p/'EXPERIMENT*.jsonl'));summaries=glob.glob(str(p/'*.summary.json'))
  if not logs or not summaries:continue
  s=json.load(open(summaries[0]));rows=[json.loads(x) for x in open(logs[0])];sub=next((x for x in rows if x.get('record_type')=='canonical_routing' and x.get('phase')=='SUBMIT'),{});resolve=next((x for x in rows if x.get('record_type')=='canonical_routing' and x.get('phase')=='RESOLVE'),{});orchestration=(resolve.get('payload') or {}).get('orchestration') or {};request=((sub.get('payload') or {}).get('orchestration') or {}).get('model_request') or {};plan=orchestration.get('decision_plan') or {};ground=plan.get('model_grounding') or {};target=ground.get('target_id');frame=(request.get('scene_summary') or {}).get('frame_id');obspath=p/'evaluation/shadow_and_evaluation_truth.jsonl';row=None
  if obspath.exists():row=next((x for line in open(obspath) if (x:=json.loads(line)).get('frame')==frame),None)
  overlaps={};verdict='模型未选择目标' if not target else '无法判断';status_reason='无有效候选或模型未选择' if not target else '无匹配投影证据'
  if row is not None and target:
   cand=next((x for x in request.get('target_grounding',{}).get('visual_candidates',[]) if x.get('target_id')==target),None)
   if cand:
    camera=np.linalg.inv(np.asarray(row['camera_world_matrix']));w,h=row['camera_width'],row['camera_height'];f=w/(2*math.tan(math.radians(row['camera_fov'])/2));box=[v*[w,h,w,h][i] for i,v in enumerate(cand['bbox_xyxy_norm'])]
    for a in row['truth_for_evaluation_only']:
     if a['role_name'].endswith(':ego'):continue
     v=np.asarray(a['vertices_world']);q=np.column_stack((v,np.ones(len(v))))@camera.T
     if (q[:,0]<=0).any():continue
     u=f*q[:,1]/q[:,0]+w/2;z=-f*q[:,2]/q[:,0]+h/2;b=[min(u),min(z),max(u),max(z)]
     inter=max(0,min(box[2],b[2])-max(box[0],b[0]))*max(0,min(box[3],b[3])-max(box[1],b[1]));union=(box[2]-box[0])*(box[3]-box[1])+(b[2]-b[0])*(b[3]-b[1])-inter;overlaps[a['role_name'].split(':')[-1]]=round(float(inter/max(union,1e-9)),3)
    matches=[r for r,v in overlaps.items() if v>=.3]
    if len(matches)>1:verdict='遮挡重叠，无法判断';status_reason='检测框与多辆车的投影 IoU 均不低于 0.3'
    elif len(matches)==1:
     verdict='与预期目标投影吻合' if matches[0]==expected else '与其他车辆投影吻合';roles={'distractor_adjacent':'相邻车道干扰车','distractor_far':'远处干扰车','lead_target':'预期前车','occluder_near':'近处遮挡车'};status_reason=f"匹配 {roles.get(matches[0],matches[0])}，IoU {overlaps[matches[0]]:.3f}；预期 {roles.get(expected,expected)}"
    else:status_reason='没有车辆的投影 IoU 达到 0.3'
  results[name]={'case':case,'model':model,'scenario_id':s.get('scenario_id'),'frame':frame,'frames':s.get('frames'),'status':s.get('status'),'completion':s.get('completion'),'collisions':s.get('collision_count'),'safety_override_frames':s.get('safety_override_frames'),'min_gap_m':s.get('min_gap_m'),'terminal':s.get('command_terminal_statuses'),'disposition':orchestration.get('disposition'),'reason':orchestration.get('reason_code'),'model_id':plan.get('model_id'),'model_grounding':ground,'target_expected':expected,'target_verdict':verdict,'target_evidence':status_reason,'projection_iou':overlaps,'failed_checks':s.get('acceptance',{}).get('failed_keys',[]),'checks':s.get('acceptance',{}).get('checks',[]),'definition':'同帧检测框与模拟车辆三维框投影的 IoU 仅是事后近似核查；多车同时重叠不判定身份。'}
tmp=BASE/'comparison_summary.tmp';tmp.write_text(json.dumps(results,ensure_ascii=False,indent=2));tmp.replace(BASE/'comparison_summary.json')
for name,r in results.items():print(name,r['model_id'],r['model_grounding'].get('target_id'),r['target_verdict'],r['disposition'],r['reason'],r['status'])
