import json,numpy as np
from eval_helpers import ROOT,datasets,truth_labels,experimental,role_for_group
profile=json.loads((ROOT/'depth_profile.json').read_text());bounds=[25,35,45,55,1e6];samples={str(v):[] for v in bounds};negative=[]
for sample in datasets('dev'):
 if sample['dataset']!='dev':continue
 labels=truth_labels(sample);d=sample['d'];matches={z['id']:z['gt_match']['role'] for z in d['evaluation']['detections'] if z['gt_match']};loc=experimental.localize_groups(sample['objects'],sample['lid'],sample['rgb'],sample['rad'],sample['ego'],alpha=1.5,depth_profile=profile)
 for g in loc['groups']:
  role,roles=role_for_group(g,matches);ng=np.asarray(g['nonground_point_indices'],dtype=int);pts=loc['lidar_ego'][ng]
  if role is None or len(pts)<3 or len(pts)>2500:continue
  med=float(np.median(np.linalg.norm(pts[:,:2],axis=1)));eps=min(1.2,max(.38,1.5*min(1.,max(.38,.018*med))));tau=experimental._limit(profile,med)
  for component in experimental._depth_components(pts,eps,tau):
   xyz=pts[component];span=np.ptp(xyz,axis=0)
   if span[0]>6.5 or span[1]>3.5 or span[2]>3:continue
   actor=sample['role_ids'][role];labs=labels[ng[component]];spread=float(np.ptp(np.linalg.norm(xyz,axis=1)));bound=next(v for v in bounds if med<v)
   if np.all(labs==actor):samples[str(bound)].append(spread)
   elif np.any(labs==actor) and np.any((labs!=actor)&(labs!=-1)):negative.append({'case':sample['key'],'spread_m':spread})
allv=[v for a in samples.values() for v in a];assert allv, 'no pure target candidate clusters available';globalmax=max(allv)+.08;bins=[]
for b in bounds:
 v=samples[str(b)];bins.append({'upper_m':b,'limit_m':max(v)+.08 if len(v)>=5 else globalmax,'pure_cluster_count':len(v),'fallback_used':len(v)<5})
result={'bins':bins,'fallback_m':bins[-1]['limit_m'],'rule':'development-only maximum pure-candidate radial spread in each distance bin plus 0.08 m matching tolerance; fewer than 5 candidates uses pooled maximum; experimental only','observed_mixed_candidates':len(negative),'warning':'no guarantee of physical vehicle bounds, validate on independent diverse scenes'};(ROOT/'geometry_profile.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');(ROOT/'geometry_calibration.json').write_text(json.dumps({'pure_spreads':samples,'mixed':negative},indent=2)+'\n');print(json.dumps(result,indent=2))
