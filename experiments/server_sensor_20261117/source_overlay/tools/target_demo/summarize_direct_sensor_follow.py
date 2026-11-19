"""Summarize no-Qwen direct control evidence; truth is evaluation-only."""
import json,glob,math,sys
from collections import Counter
from pathlib import Path
p=Path(sys.argv[1]) if len(sys.argv)>1 else Path('artifacts/runtime/direct_sensor_follow_20261112/single_20m_retry');frames=[];commands=[];feedback=[]
for l in open(glob.glob(str(p/'*.jsonl'))[0]):
 x=json.loads(l)
 if x.get('record_type')=='frame':frames.append(x)
 if x.get('record_type')=='command':commands.append(x)
 if x.get('record_type')=='feedback':feedback.append(x)
ids={x['frame'] for x in frames};rows=[json.loads(l) for l in (p/'evaluation/shadow_and_evaluation_truth.jsonl').open() if json.loads(l)['frame'] in ids];gaps=[]
for row in rows:
 ego=row['ego_world_matrix'];a=next(a for a in row['truth_for_evaluation_only'] if a['role_name'].endswith(':lead_target'));m=a['world_matrix'];gaps.append(math.hypot(ego[0][3]-m[0][3],ego[1][3]-m[1][3]))
start=rows[0]['ego_world_matrix'];end=rows[-1]['ego_world_matrix'];elapsed=frames[-1]['sim_time_s']-frames[0]['sim_time_s'];out={'frames':len(frames),'duration_s':round(elapsed,2),'command_original':commands[0]['command'].get('scenario_original_intent'),'command_runtime':commands[0]['adapted_command']['action'],'command_disposition':commands[0]['disposition'],'longitudinal_states':dict(Counter(x['longitudinal']['state'] for x in frames)),'safety_reasons':dict(Counter(x['safety']['reason'] for x in frames)),'distance_available_frames':sum(x['scene']['lead_distance_m'] is not None for x in frames),'moving_frames':sum(x['speed_mps']>.1 for x in frames),'max_speed_mps':round(max(x['speed_mps'] for x in frames),2),'final_speed_mps':round(frames[-1]['speed_mps'],2),'ego_displacement_m':round(math.hypot(end[0][3]-start[0][3],end[1][3]-start[1][3]),2),'truth_center_distance_m':{'start':round(gaps[0],2),'min':round(min(gaps),2),'end':round(gaps[-1],2)},'collision_frames':sum(x['scene']['collision'] for x in frames),'feedback':feedback}
(p/'evaluation/direct_summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
