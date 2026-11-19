"""Fail-closed compatibility guard for Student V0; no semantic imputation."""
from copy import deepcopy
def adapt_or_block(request):
    unknown=[str(t.get('target_id')) for t in request.get('targets',[]) if t.get('distance_m') is None]
    if unknown:
        return None, {'status':'BLOCKED_UNKNOWN_DISTANCE','unknown_target_ids':unknown,
                      'action':'HOLD_SAFE_STOP','reason':'Student V0 has no validity bit for distance'}
    adapted=deepcopy(request)
    adapted.pop('target_grounding',None)
    return adapted, {'status':'ALLOWED_KNOWN_DISTANCE','unknown_target_ids':[]}
