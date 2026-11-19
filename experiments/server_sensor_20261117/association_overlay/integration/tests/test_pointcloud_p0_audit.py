from types import SimpleNamespace
import carla
import numpy as np
from tools.pointcloud_p0.run_matrix import SEM_DTYPE,semantic_correspondence,radar_gt_membership

def test_semantic_matching_exact_and_unmatched():
 t=carla.Transform()
 sem=np.zeros(1,dtype=SEM_DTYPE);sem['x']=10.;sem['id']=42;sem['tag']=14
 sensor=SimpleNamespace(raw_data=sem.tobytes(),transform=t)
 pts=np.array([[10.,0.,0.],[20.,0.,0.]])
 labels=semantic_correspondence(pts,[0,1],sensor,t)
 assert labels[0]['actor_id']==42
 assert 1 not in labels

def test_radar_actor_box_membership_keeps_unmatched_separate():
 bbox=carla.BoundingBox(carla.Location(),carla.Vector3D(1,1,1))
 def actor(x):
  return SimpleNamespace(bounding_box=bbox,get_transform=lambda:carla.Transform(carla.Location(x=x)))
 actors={'A':actor(0),'B':actor(5)}
 result=radar_gt_membership(np.array([[.5,0,0],[5,0,0],[10,0,0]]),actors,'A')
 assert result['target']==1 and result['other_vehicle']==1 and result['outside_actor_boxes']==1

def test_rear_longitudinal_truth_uses_box_surface_not_center():
 from tools.pointcloud_p0.run_matrix import gt_positions
 bbox=carla.BoundingBox(carla.Location(),carla.Vector3D(2,1,1))
 actor=SimpleNamespace(bounding_box=bbox,get_transform=lambda:carla.Transform(carla.Location(x=20)))
 ego=SimpleNamespace(get_transform=lambda:carla.Transform(),get_location=lambda:carla.Location())
 result=gt_positions(actor,ego)
 assert abs(result['center_ego'][0]-20)<1e-6
 assert abs(result['box_rear_longitudinal_m']-18)<1e-6
 assert abs(result['nearest_box_distance_m']-18)<1e-6
