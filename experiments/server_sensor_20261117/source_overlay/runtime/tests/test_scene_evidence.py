from copy import deepcopy
import json
from pathlib import Path
from threading import Event

import pytest
from runtime.scene_evidence import build_evidence, parse_target_query, select_targets, verify_evidence
from runtime.orchestrator import OrchestratorConfig, PipelineOrchestrator
from voice_group.nlu_b2.parser import _extract_direction

ROOT = Path(__file__).resolve().parents[2]

def scene():
    data = json.loads((ROOT / 'interfaces/examples/perception_state.json').read_text())
    data['captured_at_ns'] = 1_100_000_000
    return data

def obj(id, x, y, cls='vehicle', sources=('RGB', 'LIDAR')):
    base = deepcopy(scene()['objects'][0])
    base.update(track_id=id, **{'class': cls}, position_m=[x, y, 0], distance_m=(x*x+y*y)**0.5, sources=list(sources))
    return base

def command(text, intent='FOLLOW'):
    return {'intent': intent, 'source_text': text, 'parameters': {}}

def plan(id='V1', behavior='FOLLOW'):
    return {'steps': [{'behavior': behavior, 'target': {'target_id': id}}]}

def check(evidence, target, current, **kwargs):
    return verify_evidence(evidence, plan(target), current, now_ns=1_150_000_000, rgb_available=True, **kwargs)

# Twelve counterfactual pairs use constructed sensor snapshots, not CARLA or Qwen measurements.
@pytest.mark.parametrize('text,objects,expected,status', [
    ('跟随右侧车辆',[obj('V1',12,-3),obj('V2',12,3)],('V1',),'RESOLVED'),
    ('跟随右侧车辆',[obj('V1',12,3),obj('V2',12,-3)],('V2',),'RESOLVED'),
    ('跟随左侧车辆',[obj('V1',12,-3),obj('V2',12,3)],('V2',),'RESOLVED'),
    ('跟随左侧车辆',[obj('V1',12,3),obj('V2',12,-3)],('V1',),'RESOLVED'),
    ('跟随最近的车辆',[obj('V1',10,0),obj('V2',20,0)],('V1',),'RESOLVED'),
    ('跟随最近的车辆',[obj('V1',20,0),obj('V2',10,0)],('V2',),'RESOLVED'),
    ('跟随最近的车辆',[obj('V1',8,0),obj('V2',30,0)],('V1',),'RESOLVED'),
    ('跟随最近的车辆',[obj('V1',30,0),obj('V2',8,0)],('V2',),'RESOLVED'),
    ('跟随右侧车辆',[obj('V1',12,-3)],('V1',),'RESOLVED'),
    ('跟随右侧车辆',[obj('V1',12,-3),obj('V2',20,-3)],('V1','V2'),'AMBIGUOUS'),
    ('跟随较近的车辆',[obj('V1',12,0)],('V1',),'RESOLVED'),
    ('跟随较近的车辆',[obj('V1',12,0),obj('V2',20,0)],('V1','V2'),'AMBIGUOUS'),
    ('避让右侧公交车',[obj('V1',12,-3)],('V1',),'AMBIGUOUS'),
    ('避让右侧公交车',[obj('V2',12,-3)],('V2',),'AMBIGUOUS'),
    ('跟随右侧白色车辆',[obj('V1',12,-3)],('V1',),'AMBIGUOUS'),
    ('跟随右侧白色车辆',[obj('V1',12,-3),obj('V2',20,-3)],('V1','V2'),'AMBIGUOUS'),
    ('跟随右侧车辆',[obj('V1',12,-3)],('V1',),'RESOLVED'),
    ('跟随右侧车辆',[obj('V1',12,3)],(),'UNRESOLVED'),
    ('避让前方行人',[obj('P1',10,0,'pedestrian')],('P1',),'RESOLVED'),
    ('避让前方行人',[obj('V1',10,0)],(),'UNRESOLVED'),
    ('从左边绕过右侧车辆',[obj('V1',10,-3),obj('V2',10,3)],('V1',),'RESOLVED'),
    ('从右边绕过左侧车辆',[obj('V1',10,-3),obj('V2',10,3)],('V2',),'RESOLVED'),
    ('从左边绕过右侧车辆',[obj('V1',10,-3)],('V1',),'RESOLVED'),
    ('从右边绕过左侧车辆',[obj('V1',10,-3)],(),'UNRESOLVED'),
])
def test_counterfactual_snapshots(text,objects,expected,status):
    s=scene(); s['objects']=objects
    e=build_evidence(command(text,'AVOID_OBSTACLE' if '避让' in text or '绕过' in text else 'FOLLOW'),s)
    assert (e.candidate_ids,e.status)==(expected,status)

def test_direction_and_ambiguous_visual_are_independent():
    text='从左边绕过右侧那辆较近的公交车'
    q=parse_target_query(text,'AVOID_OBSTACLE')
    assert (q.side,q.subtype,q.distance_relation)==('RIGHT','bus','NEAR')
    assert _extract_direction(text)=='LEFT'
    assert _extract_direction('向左变道再向右变道')=='CONFLICT'
    assert parse_target_query('从左边绕过车辆','AVOID_OBSTACLE').side is None

def test_quality_and_safety_selection():
    s=scene(); s['objects']=[obj('risk'+str(i),i+1,0,'obstacle') for i in range(8)]+[obj('V1',40,-3)]
    e=build_evidence(command('跟随右侧车辆'),s)
    assert 'V1' in [o['track_id'] for o in select_targets(s,e,8)]
    assert [o['track_id'] for o in select_targets(s,e,8)][:3]==['risk0','risk1','risk2']
    assert build_evidence(command('跟随右侧车辆'),s,geometry_trusted=False).uncertain_geometry
    assert build_evidence(command('跟随车辆'),s,ids_reliable=False).reason=='TRACK_ID_UNSTABLE'

def test_wrong_lost_stale_and_visual_unavailable():
    s=scene(); s['objects']=[obj('V1',10,-3),obj('V2',12,3)]
    e=build_evidence(command('跟随右侧车辆'),s)
    assert check(e,'V1',s)[0]=='PASS'
    assert check(e,'V2',s)==('REJECT','TARGET_ID_MISMATCH')
    s['objects']=[obj('V2',12,3)]
    assert check(e,'V1',s)==('CONFIRM','TARGET_LOST')
    assert verify_evidence(e,plan('V1'),s,now_ns=2_000_000_000,rgb_available=True)==('CONFIRM','PERCEPTION_EXPIRED')
    s['objects']=[obj('V1',10,-3)]
    ev=build_evidence(command('跟随右侧公交车'),s)
    assert verify_evidence(ev,plan(),s,now_ns=1_150_000_000,rgb_available=False)==('CONFIRM','VISUAL_UNAVAILABLE')
    assert verify_evidence(ev,plan(None,'STOP'),s,now_ns=2_000_000_000,rgb_available=False)[0]=='PASS'

def test_action_rules_allow_safety_and_reject_contradiction():
    s=scene(); s['objects']=[obj('V1',10,-3)]
    e=build_evidence(command('跟随右侧车辆'),s)
    cmd=command('跟随右侧车辆')
    assert verify_evidence(e,plan('V1','CHANGE_LANE_LEFT'),s,now_ns=1_150_000_000,rgb_available=True,command=cmd)==('REJECT','ACTION_CONTRADICTS_FOLLOW')
    assert verify_evidence(e,plan(None,'STOP'),s,now_ns=1_150_000_000,rgb_available=False,command=cmd)[0]=='PASS'

def test_async_rechecks_target_after_inference():
    s=scene(); s['objects']=[obj('V1',10,-3)]
    c=json.loads((ROOT/'interfaces/examples/driving_command.json').read_text())
    c.update(command_id='evidence-async',source_text='跟随右侧车辆',intent='FOLLOW',parameters={})
    start, release=Event(), Event()
    def infer(req):
        start.set(); assert release.wait(1)
        p=json.loads((ROOT/'interfaces/examples/maneuver_plan.json').read_text())
        p.update(request_id=req['request_id'],command_id=req['command_id'],created_at_ns=req['created_at_ns'],valid_until_ns=req['deadline_ns'])
        step=p['steps'][0]; step['behavior']='FOLLOW'; step['target'].update(target_id='V1',target_lane='CURRENT',time_gap_s=2.0); step['completion']={'type':'TARGET_GAP_REACHED','value':2.0,'lane':None,'hold_frames':3}; step['preconditions']=['PERCEPTION_FRESH']
        p['steps']=[step]
        return p
    with PipelineOrchestrator(infer=infer,config=OrchestratorConfig(qwen_mode='planner_v2',model_timeout_ms=1000)) as rt:
        rt.submit_command(c,s,now_ns=1_100_000_000)
        assert start.wait(1)
        latest=deepcopy(s); latest['frame_id']+=1; latest['captured_at_ns']=1_120_000_000; latest['objects']=[]
        rt.publish_perception(latest); release.set()
        result=rt.poll_slow(now_ns=1_150_000_000,wait_timeout_ms=1000)
    assert result and result[0].reason_code=='SEMANTIC_TARGET_LOST'
    assert result[0].control_command is None

def test_visual_ambiguity_is_routed_only_with_image_and_trust():
    s=scene(); s['objects']=[obj('V1',12,-3),obj('V2',20,-3)]
    c=json.loads((ROOT/'interfaces/examples/driving_command.json').read_text())
    c.update(command_id='visual-routing',source_text='跟随右侧那辆公交车',intent='FOLLOW',parameters={})
    with PipelineOrchestrator(infer=lambda request: {},config=OrchestratorConfig(qwen_mode='planner_v2')) as rt:
        result=rt.submit_command(c,s,now_ns=1_100_000_000,rgb_ref='frame.png')
        assert result.model_request['routing']['disposition']=='QWEN_PLAN'
        assert 'FOLLOW' in result.model_request['constraints']['allowed_behaviors']
    with PipelineOrchestrator(infer=lambda request: {},config=OrchestratorConfig(qwen_mode='planner_v2')) as rt:
        result=rt.submit_command(c,s,now_ns=1_100_000_000)
        assert result.model_request['constraints']['allowed_behaviors']==['STOP']
    c['confidence']=0.2
    with PipelineOrchestrator(infer=lambda request: {},config=OrchestratorConfig(qwen_mode='planner_v2')) as rt:
        result=rt.submit_command(c,s,now_ns=1_100_000_000,rgb_ref='frame.png')
        assert result.model_request['constraints']['allowed_behaviors']==['STOP']

def test_unique_binding_reaches_existing_model_hint_and_keeps_schema():
    s=scene(); s['objects']=[obj('V1',12,-3),obj('V2',20,3)]
    c=json.loads((ROOT/'interfaces/examples/driving_command.json').read_text())
    c.update(source_text='跟随右侧车辆',intent='FOLLOW',parameters={})
    with PipelineOrchestrator(infer=lambda request: {},config=OrchestratorConfig(qwen_mode='planner_v2')) as rt:
        result=rt.submit_command(c,s,now_ns=1_100_000_000)
        assert result.model_request['command_hint']['target']=='V1'

def test_avoidance_lane_must_match_maneuver_direction():
    s=scene(); s['objects']=[obj('V1',12,-3)]
    cmd={'intent':'AVOID_OBSTACLE','source_text':'从左边绕过右侧车辆','parameters':{'direction':'LEFT'}}
    e=build_evidence(cmd,s)
    p={'steps':[{'behavior':'AVOID_OBSTACLE','target':{'target_id':'V1','target_lane':'RIGHT_ADJACENT'}}]}
    assert verify_evidence(e,p,s,now_ns=1_150_000_000,rgb_available=True,command=cmd)==('REJECT','ACTION_DIRECTION_MISMATCH')

def test_low_confidence_never_produces_a_trusted_binding():
    s=scene(); low=obj('V1',10,-3); low['confidence']=0.3; s['objects']=[low]
    e=build_evidence(command('跟随右侧车辆'),s)
    assert e.status=='AMBIGUOUS' and e.reason=='LOW_TARGET_CONFIDENCE'
    assert check(e,'V1',s)==('CONFIRM','LOW_TARGET_CONFIDENCE')

def test_model_cannot_choose_candidate_omitted_from_input():
    s=scene(); s['objects']=[obj('V1',10,-3),obj('V2',20,-3)]
    e=build_evidence(command('跟随右侧那辆车'),s)
    assert verify_evidence(e,plan('V2'),s,now_ns=1_150_000_000,rgb_available=True,visible_ids={'V1'})==('REJECT','TARGET_NOT_IN_MODEL_INPUT')

def test_urgent_ttc_is_retained_over_farther_safe_objects():
    s=scene(); s['objects']=[obj('near'+str(i),i+1,0,'obstacle') for i in range(8)]+[obj('urgent',40,0,'obstacle')]
    s['objects'][-1]['ttc_s']=0.8
    assert 'urgent' in [o['track_id'] for o in select_targets(s,build_evidence(command('跟随车辆'),s),3)]


def test_avoidance_without_specified_lane_requires_confirmation():
    s=scene(); s['objects']=[obj('V1',12,-3)]
    cmd={'intent':'AVOID_OBSTACLE','source_text':'从左边绕过右侧车辆','parameters':{'direction':'LEFT'}}
    e=build_evidence(cmd,s)
    assert verify_evidence(e,plan('V1','AVOID_OBSTACLE'),s,now_ns=1_150_000_000,rgb_available=True,command=cmd)==('CONFIRM','ACTION_DIRECTION_UNSPECIFIED')

def test_position_after_object_is_parsed():
    assert parse_target_query('跟随那辆车在右侧','FOLLOW').side=='RIGHT'


def test_lane_direction_is_not_mistaken_for_object_side():
    assert _extract_direction('麻烦换左边车道') == 'LEFT'
    assert _extract_direction('进入右侧车道') == 'RIGHT'


def test_world_truth_alone_is_not_sensor_grounding():
    s=scene(); s['objects']=[obj('V1',10,-3,sources=('WORLD',))]
    e=build_evidence(command('跟随右侧车辆'),s)
    assert e.status=='UNRESOLVED' and e.reason=='WORLD_ONLY_NOT_SENSOR_EVIDENCE'

def test_ambiguous_target_requires_model_choice_and_all_candidates_visible():
    s=scene();s['objects']=[obj('V1',10,-3),obj('V2',20,-3)]
    e=build_evidence(command('跟随右侧那辆车'),s)
    p=plan('V2')
    assert verify_evidence(e,p,s,now_ns=1_150_000_000,rgb_available=True,visualized_ids={'V1','V2'})==('CONFIRM','MODEL_VISUAL_SELECTION_MISSING')
    p['model_grounding']={'selection_source':'MODEL_VISUAL','target_id':'V2','abstained':False,'raw_choice':'B'}
    assert verify_evidence(e,p,s,now_ns=1_150_000_000,rgb_available=True,visualized_ids={'V1'})==('CONFIRM','VISUAL_CANDIDATES_INCOMPLETE')
    assert verify_evidence(e,p,s,now_ns=1_150_000_000,rgb_available=True,visualized_ids={'V1','V2'})[0]=='PASS'

def test_blocking_poll_counts_wait_time_for_sensor_freshness():
    import time
    s=scene();s['objects']=[obj('V1',10,-3)]
    c=json.loads((ROOT/'interfaces/examples/driving_command.json').read_text())
    c.update(command_id='freshness-wait',source_text='跟随那辆车',intent='FOLLOW',parameters={})
    def infer(req):
        time.sleep(.65)
        p=json.loads((ROOT/'interfaces/examples/maneuver_plan.json').read_text())
        p.update(request_id=req['request_id'],command_id=req['command_id'],created_at_ns=req['created_at_ns'],valid_until_ns=req['deadline_ns'])
        step=p['steps'][0];step['behavior']='FOLLOW';step['target'].update(target_id='V1',target_lane='CURRENT',time_gap_s=2.0)
        step['completion']={'type':'TARGET_GAP_REACHED','value':2.0,'lane':None,'hold_frames':3};step['preconditions']=['PERCEPTION_FRESH'];p['steps']=[step]
        return p
    with PipelineOrchestrator(infer=infer,config=OrchestratorConfig(qwen_mode='planner_v2',model_timeout_ms=2000)) as rt:
        rt.submit_command(c,s,now_ns=1_100_000_000)
        result=rt.poll_slow(now_ns=1_100_000_000,wait_timeout_ms=1500)
    assert result and result[0].reason_code=='SEMANTIC_PERCEPTION_EXPIRED'
    assert result[0].control_command is None

def test_lane_and_distance_select_nearest_verified_vehicle_without_unknowns():
    s=scene(); a=obj('same-near',10,0); a['lane_relation']='SAME';a['geometry_source']='RGB_LIDAR_PROJECTED'
    b=obj('same-far',20,0);b['lane_relation']='SAME';b['geometry_source']='RGB_LIDAR_PROJECTED'
    c=obj('other',8,-3);c['lane_relation']='OTHER';c['geometry_source']='RGB_LIDAR_PROJECTED'
    s['objects']=[a,b,c]
    e=build_evidence(command('跟随最近的同车道前方车辆'),s)
    assert e.status=='RESOLVED' and e.resolved_id=='same-near'
    c['lane_relation']='UNKNOWN';e=build_evidence(command('跟随最近的同车道前方车辆'),s)
    assert e.status=='AMBIGUOUS' and 'other' in e.candidate_ids

def test_unvalidated_sensor_projection_does_not_authorize_follow():
    s=scene(); s['objects']=[obj('V1',10,-3)]
    c=json.loads((ROOT/'interfaces/examples/driving_command.json').read_text())
    c.update(command_id='unvalidated',source_text='跟随那辆车',intent='FOLLOW',parameters={})
    def infer(req):
        p=json.loads((ROOT/'interfaces/examples/maneuver_plan.json').read_text())
        p.update(request_id=req['request_id'],command_id=req['command_id'],created_at_ns=req['created_at_ns'],valid_until_ns=req['deadline_ns'])
        step=p['steps'][0];step['behavior']='FOLLOW';step['target'].update(target_id='V1',target_lane='CURRENT',time_gap_s=2.0)
        step['completion']={'type':'TARGET_GAP_REACHED','value':2.0,'lane':None,'hold_frames':3};step['preconditions']=['PERCEPTION_FRESH'];p['steps']=[step]
        return p
    with PipelineOrchestrator(infer=infer,config=OrchestratorConfig(qwen_mode='planner_v2',model_timeout_ms=2000)) as rt:
        rt.submit_command(c,s,now_ns=1_100_000_000,runtime_state={'target_geometry_source':'PER_OBJECT_UNVALIDATED'})
        result=rt.poll_slow(now_ns=1_150_000_000,wait_timeout_ms=1000)
    assert result and result[0].reason_code=='SEMANTIC_GEOMETRY_NOT_VALIDATED'
    assert result[0].control_command is None
