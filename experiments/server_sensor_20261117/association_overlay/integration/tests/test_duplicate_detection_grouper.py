from types import SimpleNamespace
from integration.duplicate_detection_grouper import DuplicateDetectionGrouper

def obj(i,c='car',box=(.1,.1,.3,.3)):
 return SimpleNamespace(track_id=i,class_name=c,confidence=.9,bbox_xyxy_norm=box)
def cluster(points=range(10),x=12):
 return {'status':'LOCATED_UNVALIDATED','cluster_count':len(points),'cluster_center_ego':[x,0,1],'selected_point_indices':list(points),'clusters':[{'count':len(points),'median_forward_m':x}]}
def test_different_vehicle_subclasses_can_group_with_shared_3d_cluster():
 import numpy as np
 a,b=obj('a'),obj('b','truck');groups,e=DuplicateDetectionGrouper().group([a,b],{'a':cluster(),'b':cluster()},lidar_ego=np.zeros((10,3)))
 assert len(groups)==1 and len(groups[0].members)==2 and e[0]['reason']=='CONSISTENT_BOX_AND_CLUSTER'
def test_high_iou_alone_does_not_merge_distinct_clusters_or_stable_tracks():
 a,b=obj('a'),obj('b');d=DuplicateDetectionGrouper()
 for results,h in [({'a':cluster(),'b':cluster(range(10,20),15)},None),({'a':cluster(),'b':cluster()},{'a':{'stable':True,'track_id':'one'},'b':{'stable':True,'track_id':'two'}})]:
  groups,e=d.group([a,b],results,h);assert len(groups)==2 and e[0]['decision']=='SEPARATE'
def test_insufficient_data_keeps_two_hypotheses():
 a,b=obj('a'),obj('b','truck');g,e=DuplicateDetectionGrouper().group([a,b],{'a':cluster(),'b':{'status':'UNKNOWN'}});assert len(g)==2 and e[0]['reason']=='INSUFFICIENT_3D_EVIDENCE'
def test_incompatible_classes_and_competing_depths_are_not_merged():
 a,b=obj('a'),obj('b','pedestrian');g,_=DuplicateDetectionGrouper().group([a,b],{'a':cluster(),'b':cluster()});assert len(g)==2
 b=obj('b');c=cluster();c['clusters'].append({'count':4,'median_forward_m':16});g,e=DuplicateDetectionGrouper().group([a,b],{'a':cluster(),'b':c});assert len(g)==2 and e[0]['reason']=='COMPETING_DEPTH_CLUSTERS'

def test_recorded_night_overlap_has_single_owner_and_preserves_uncertain_points():
 import pathlib,numpy as np
 from tools.pointcloud_p0.replay_io import read
 from integration.target_group_localization import localize_groups,ASSIGNED,AMBIGUOUS,ENVIRONMENT
 p=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_p0_rear_final_20261117/night/0')
 if not p.exists():
  import pytest;pytest.skip('server-side recording not available')
 d,l,r,rad,e,o=read(p);x=localize_groups(o,l,r,rad,e)
 group=next(g for g in x['groups'] if {'C-0002','C-0003'}=={m['id'] for m in g['members']});assert group['status']=='LOCATED_UNVALIDATED' and group['cluster_count']==18
 common=set(d['predictions'][1]['box_point_indices'])&set(d['predictions'][2]['box_point_indices']);assert len(common)==53
 assert sum(x['point_state'][i]==ASSIGNED for i in common)==18 and sum(x['point_state'][i]==AMBIGUOUS for i in common)==35
 assert np.all(x['point_owner'][x['point_state']!=ASSIGNED]==-1)
 selected=[i for g in x['groups'] for i in g['selected_point_indices']];assert len(selected)==len(set(selected)) and len(selected)==int((x['point_state']==ASSIGNED).sum())
 assert group['quality']['vehicle_center_supported'] is False and group['quality']['vehicle_occupancy_supported'] is False


def test_second_possible_depth_prevents_automatic_merge():
 import numpy as np
 a,b=obj('a'),obj('b','truck');p=cluster();q=cluster();p['nonground_point_indices']=[0,1];q['nonground_point_indices']=[0,1]
 xyz=np.array([[12.,0.,1.],[20.,0.,1.]])
 groups,e=DuplicateDetectionGrouper().group([a,b],{'a':p,'b':q},lidar_ego=xyz)
 assert len(groups)==2 and e[0]['reason']=='POSSIBLE_SECOND_DEPTH'
