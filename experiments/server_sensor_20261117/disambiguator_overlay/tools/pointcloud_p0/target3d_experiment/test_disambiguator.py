import numpy as np
import pytest
from .disambiguator import TargetObservation,PairObservation,ResearchPolicy,Target3DDisambiguator,disambiguate

def target(name,frame,timestamp,offset,ids=(1,2,3),cluster=None,sensor='lidar'):
    ids=np.array(ids,dtype=np.int64);points=np.array([[offset,0,0],[offset+.1,0,0],[offset+.2,0,0]],dtype=float)[:len(ids)]
    return TargetObservation(name,frame,timestamp,sensor,(.1,.1,.5,.5),ids,points,ids.copy() if cluster is None else np.array(cluster,dtype=np.int64))
def pair(frame=1,t=1.,separation=8.):
    return PairObservation(target('formal',frame,t,10.),target('aux',frame,t,10.+separation,ids=(4,5,6)))
def policy():return ResearchPolicy(3,1.,1.,2,.2,1)
def test_single_frame_has_metrics_but_never_confirms_identity():
    r=disambiguate(pair());assert r['status']=='UNKNOWN';assert 'TEMPORAL_EVIDENCE_MISSING' in r['reasons'];assert 'THRESHOLDS_NOT_CALIBRATED' in r['reasons'];assert r['current']['radial_interval_gap_m']==pytest.approx(7.8);assert r['current']['bbox_iou']==pytest.approx(1.);assert not r['formal_control_authority']
def test_point_overlap_fails_closed_even_with_separation():
    r=disambiguate(PairObservation(target('formal',1,1.,10.),target('aux',1,1.,20.,ids=(3,4,5))));assert r['status']=='UNKNOWN';assert r['current']['duplicate_point_ids']==[3];assert 'DUPLICATE_POINT_OWNERSHIP' in r['reasons']
def test_sensor_frame_or_timestamp_mismatch_is_not_identity_evidence():
    r=disambiguate(PairObservation(target('formal',1,1.,10.),target('aux',2,1.01,20.,ids=(4,5,6))));assert {'FRAME_OR_SENSOR_MISMATCH','TIMESTAMP_MISMATCH'}<=set(r['reasons'])
def test_actual_prior_observations_required_for_research_support():
    r=disambiguate(pair(2,1.1),history=[pair(1,1.)],policy=policy());assert r['status']=='INDEPENDENT_3D_HYPOTHESES_SUPPORTED_UNVALIDATED';assert not r['formal_control_authority'];assert not r['vehicle_center_or_extent_established']
def test_time_or_identity_discontinuity_rejected():
    r=disambiguate(pair(3,1.3),history=[pair(1,1.)],policy=policy());assert r['status']=='UNKNOWN';assert 'HISTORY_NOT_CONSECUTIVE' in r['reasons']
def test_near_or_overlapping_depth_cannot_be_confirmed():
    r=disambiguate(pair(2,1.1,.1),history=[pair(1,1.,.1)],policy=policy());assert r['status']=='UNKNOWN';assert 'DEPTH_SEPARATION_UNCERTAIN' in r['reasons']
def test_missing_formal_or_missing_cluster_fail_closed():
    aux=target('aux',1,1.,20.,ids=(4,5,6));assert 'NO_FORMAL_TARGET' in disambiguate(PairObservation(None,aux))['reasons'];empty=target('aux',1,1.,20.,ids=(4,5,6),cluster=[]);assert 'NO_AUXILIARY_CLUSTER' in disambiguate(PairObservation(target('formal',1,1.,10.),empty))['reasons']
def test_rejects_foreign_cluster_points_and_uncalibrated_policy():
    aux=target('aux',1,1.,20.,ids=(4,5,6),cluster=[9]);assert disambiguate(PairObservation(target('formal',1,1.,10.),aux))['reasons']==['INVALID_OBSERVATION']
    with pytest.raises(ValueError):ResearchPolicy(3,0.,1.,2,.2,1).validate()

def test_skipped_frame_is_not_consecutive_even_if_timestamp_is_close():
    r=disambiguate(pair(3,1.1),history=[pair(1,1.)],policy=policy());assert r['status']=='UNKNOWN';assert 'HISTORY_NOT_CONSECUTIVE' in r['reasons']
def test_missing_cluster_is_reported_even_when_formal_detection_absent():
    aux=target('aux',1,1.,20.,ids=(4,5,6),cluster=[]);r=disambiguate(PairObservation(None,aux));assert {'NO_FORMAL_TARGET','NO_AUXILIARY_CLUSTER'}<=set(r['reasons'])
def test_repeated_point_ids_within_candidate_are_invalid():
    aux=target('aux',1,1.,20.,ids=(4,4,5));r=disambiguate(PairObservation(target('formal',1,1.,10.),aux));assert r['status']=='UNKNOWN' and 'INVALID_OBSERVATION' in r['reasons']
def test_sensor_only_module_has_no_oracle_imports():
    import ast,pathlib
    source=pathlib.Path(__file__).with_name('disambiguator.py').read_text();tree=ast.parse(source);imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]+[a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names];assert not any(x and ('carla' in x.lower() or 'semantic' in x.lower()) for x in imports)

def test_class_facade_has_same_fail_closed_sensor_result():
    assert Target3DDisambiguator().evaluate(pair()) == disambiguate(pair())
