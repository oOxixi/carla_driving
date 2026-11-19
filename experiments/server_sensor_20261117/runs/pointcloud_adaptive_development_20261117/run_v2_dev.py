import json,time,collections
import numpy as np
from eval_helpers import ROOT,datasets,truth_labels,experimental,evaluate,assert_same_precluster
profile=json.loads((ROOT/'depth_profile.json').read_text());v1=json.loads((ROOT/'v1_development_frames.json').read_text());ranking=[]
for alpha in (1.1,1.2,1.3,1.4,1.5):
 x=[r for r in v1 if r['dataset']=='dev' and r['variant']==f'alpha_{alpha}'];counts=collections.Counter();[counts.update(r['point_counts']) for r in x];den=counts['target']+counts['background']+counts['other_vehicle'];prec=counts['target']/den if den else 0.;ranking.append({'alpha':alpha,'coverage':sum(r['located'] for r in x),'recall_points':sum(r['recall_numerator'] for r in x),'precision':prec,'merged_detection_groups':sum(r['merged_detection_groups'] for r in x)})
eligible=[x for x in ranking if x['precision']>=.99 and x['merged_detection_groups']==0];assert eligible;best=max(eligible,key=lambda x:(x['coverage'],x['recall_points'],-x['alpha']));assert best['alpha']==1.5
(ROOT/'v1_parameter_lock.json').write_text(json.dumps({'selected':best,'ranking':ranking,'rule':'development new scenes only; eligible precision >=99%, no merged matched detection groups; maximize localized expected vehicles, then matched-box point recall numerator, then smaller alpha; oldA and holdout not used for selection','warning':'exploratory selection, candidate point-level merges separately require audit'},indent=2)+'\n');rows=[];checks=0
for n,sample in enumerate(datasets('dev')):
 labels=truth_labels(sample);args=(sample['objects'],sample['lid'],sample['rgb'],sample['rad'],sample['ego']);outputs={}
 for name in np.random.default_rng(1911+n).permutation(['V1','V2']):
  kw={'alpha':best['alpha']};
  if name=='V2':kw['depth_profile']=profile
  start=time.perf_counter_ns();loc=experimental.localize_groups(*args,**kw);elapsed=(time.perf_counter_ns()-start)/1e6;outputs[name]=loc;record=evaluate(sample,loc,labels,elapsed);record['variant']=name;rows.append(record)
 assert_same_precluster(outputs['V1'],outputs['V2']);checks+=1
 print('DONE',sample['dataset'],sample['key'],flush=True)
(ROOT/'v2_development_frames.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print('COMPLETE',len(rows),'unchanged preceding checks',checks)
