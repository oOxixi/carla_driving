import json,collections,numpy as np
from eval_helpers import ROOT,datasets,truth_labels,experimental
bins=[25,35,45,55,1e6];data={str(z):{'same':[],'different':[]} for z in bins};records=[]
for sample in datasets('dev'):
 if sample['dataset']!='dev':continue
 labels=truth_labels(sample);loc=experimental.localize_groups(sample['objects'],sample['lid'],sample['rgb'],sample['rad'],sample['ego'],alpha=1.5);actors=set(sample['role_ids'].values())
 for group in loc['groups']:
  ng=np.asarray(group['nonground_point_indices'],dtype=int);pts=loc['lidar_ego'][ng]
  if len(pts)<2:continue
  med=float(np.median(np.linalg.norm(pts[:,:2],axis=1)));b=next(x for x in bins if med<x);epsilon=min(1.2,max(.38,1.5*min(1.,max(.38,.018*med))));rad=np.linalg.norm(pts,axis=1);ds=np.linalg.norm(pts[:,None,:]-pts[None,:,:],axis=2)
  for i in range(len(pts)):
   for j in range(i+1,len(pts)):
    if ds[i,j]>epsilon:continue
    a,bid=int(labels[ng[i]]),int(labels[ng[j]])
    if a in actors and bid==a:kind='same'
    elif (a in actors and bid!=-1 and a!=bid) or (bid in actors and a!=-1 and a!=bid):kind='different'
    else:continue
    data[str(b)][kind].append(float(abs(rad[i]-rad[j])))
all_same=[v for z in data.values() for v in z['same']];assert len(all_same)>=10,('insufficient positive depth pairs',len(all_same));global95=float(np.percentile(all_same,95));profile={'bins':[],'fallback_m':global95,'rule':'per distance bin 95th percentile of within-actor radial differences for geometrically connectable development-only pairs; fewer than 10 pairs uses pooled 95th percentile','model_selection_only':'experimental; no production threshold approved'}
summary={}
for upper in bins:
 z=data[str(upper)];v=z['same'];negative=z['different'];limit=float(np.percentile(v,95)) if len(v)>=10 else global95;profile['bins'].append({'upper_m':upper,'limit_m':limit,'positive_pairs':len(v),'negative_pairs':len(negative),'fallback_used':len(v)<10});summary[str(upper)]={'positive':len(v),'negative':len(negative),'limit':limit,'positive_retained':sum(t<=limit for t in v),'negative_retained':sum(t<=limit for t in negative),'positive_minmax':[min(v),max(v)] if v else None,'negative_minmax':[min(negative),max(negative)] if negative else None}
profile['fallback_m']=profile['bins'][-1]['limit_m'];(ROOT/'depth_profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n');(ROOT/'depth_calibration.json').write_text(json.dumps({'summary':summary,'pairs':data,'total_positive':len(all_same)},indent=2)+'\n');print(json.dumps(summary,indent=2));print('global95',global95,'total',len(all_same))
