import json,os
from pathlib import Path
import numpy as np
p=Path(os.environ['POINTCLOUD_P0_OUTPUT']);rows=[]
for f in p.glob('*/*/result.json'):
 d=json.loads(f.read_text());objs={o['id']:o for o in d['predictions']}
 for e in d['evaluation']['detections']:
  if e.get('errors'):rows.append({'case':d['case'],'repeat':d['repeat'],'id':e['id'],'count':objs[e['id']]['cluster_count'],'error_m':abs(e['errors']['nearest_surface_range_error_m'])})
out={'method':'post-hoc filter of already localized samples; not independently validated, not an acceptance rule','already_located':len(rows),'total_expected':json.loads((p/'summary.json').read_text())['overall']['expected'],'rules':[],'worst':max(rows,key=lambda z:z['error_m'])}
for n in (3,5,8):
 selected=[r for r in rows if r['count']>=n];vals=[r['error_m'] for r in selected]
 out['rules'].append({'minimum_points':n,'retained':len(vals),'excluded':len(rows)-len(vals),'p50':float(np.percentile(vals,50)) if vals else None,'p95':float(np.percentile(vals,95)) if vals else None,'maximum':max(vals) if vals else None})
(p/'sensitivity.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False))
