import json,numpy as np
from eval_helpers import ROOT,datasets,truth_labels,experimental,original,assert_same_precluster
rng=np.random.default_rng(91)
for n in range(3,25):
 p=rng.normal(size=(n,3));assert [x.tolist() for x in experimental._depth_components(p,.7,None)]==[x.tolist() for x in original._clusters(p,.7)]
p=np.array([[10.,0.,0.],[10.1,0.,0.],[10.2,0.,0.],[10.8,0.,0.],[10.9,0.,0.],[11.,0.,0.]])
base=experimental._depth_components(p,.7,None);cut=experimental._depth_components(p,.7,.25);assert len(base)==1 and len(base[0])==6 and len(cut)==2 and sorted(map(len,cut))==[3,3]
forced={'bins':[{'upper_m':1e9,'limit_m':1e-8}],'fallback_m':1e-8};found=False
for s in datasets('dev'):
 if s['dataset']!='dev':continue
 args=(s['objects'],s['lid'],s['rgb'],s['rad'],s['ego']);a=experimental.localize_groups(*args,alpha=1.5);b=experimental.localize_groups(*args,alpha=1.5,geometry_profile=forced);assert_same_precluster(a,b)
 for g in b['groups']:
  if g['reason']=='GEOMETRY_REJECTED_OR_AMBIGUOUS':
   assert g['status']=='UNKNOWN' and not g['selected_point_indices'];found=True
 if found:break
assert found
print('PASS: original connected-component parity; depth separated synthetic clusters; rejected geometry remains UNKNOWN with no assigned points; precluster ownership unchanged.')
(ROOT/'test_invariants.json').write_text(json.dumps({'cluster_parity':True,'depth_separation_synthetic':True,'geometry_rejected_unknown_no_assigned':True,'precluster_unchanged':True},indent=2)+'\n')
