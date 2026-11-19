"""Experimental wrapper: experimental distance-ordered Student V0 inference; not a lane-selection fix."""
from copy import deepcopy
from math import isfinite
def canonical_request(request):
    req=deepcopy(request)
    ids=[x.get('target_id') for x in req.get('targets',[])]
    if any(not isinstance(i,str) or not i for i in ids) or len(ids)!=len(set(ids)):
        raise ValueError('candidate IDs must be nonempty and unique')
    if len(ids)>8:
        raise ValueError('too many candidates for Student V0')
    if any(not isinstance(x.get('distance_m'),(int,float)) or isinstance(x.get('distance_m'),bool) or not isfinite(x['distance_m']) or x['distance_m']<0 for x in req.get('targets',[])):
        raise ValueError('unknown distance: fail closed')
    req['targets'].sort(key=lambda x:x['distance_m'])
    if any(b['distance_m']-a['distance_m']<1.0 for a,b in zip(req['targets'],req['targets'][1:])):
        raise ValueError('candidate distances too close to rank reliably')
    req.pop('target_grounding',None)
    return req
