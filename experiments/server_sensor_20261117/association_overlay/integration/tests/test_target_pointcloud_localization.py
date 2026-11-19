from types import SimpleNamespace
import numpy as np
import pytest
from integration.target_pointcloud_localization import localize,_ground_plane

class Transform:
 def get_matrix(self):return np.eye(4).tolist()
 def get_inverse_matrix(self):return np.eye(4).tolist()
class Radar(list):
 frame=5;timestamp=.25;transform=Transform()
def sensor_points(ambiguous=False):
 rng=np.random.default_rng(7)
 ground=np.column_stack((rng.uniform(2,30,900),rng.uniform(-9,9,900),np.full(900,-.35)))
 a=np.column_stack((rng.normal(10,.08,25),rng.normal(0,.08,25),rng.normal(.5,.08,25)))
 b=np.column_stack((rng.normal(20,.08,25),rng.normal(0,.08,25),rng.normal(.5,.08,25)))
 return np.vstack((ground,a,b if ambiguous else np.empty((0,3))))
def measurements(points):
 raw=np.column_stack((points,np.ones(len(points)))).astype(np.float32)
 lidar=SimpleNamespace(frame=5,timestamp=.25,transform=Transform(),raw_data=raw.tobytes())
 rgb=SimpleNamespace(frame=5,timestamp=.25,transform=Transform(),width=800,height=450)
 obj=SimpleNamespace(track_id='x',class_name='car',confidence=.9,bbox_xyxy_norm=(.4,.35,.6,.6))
 return obj,lidar,rgb

def test_ground_estimation_rejects_elevated_points():
 p=sensor_points();plane=_ground_plane(p)
 assert plane is not None and abs(plane['c']+.35)<.03
def test_projection_ground_filter_and_single_cluster():
 obj,lidar,rgb=measurements(sensor_points())
 result=localize([obj],lidar,rgb,Radar(),Transform())
 r=result['objects'][0]
 assert r['status']=='LOCATED_UNVALIDATED'
 assert len(r['selected_point_indices'])>=20
 assert abs(r['cluster_center_ego'][0]-10)<.2
 assert r['nearest_surface_distance_m']>9
def test_multiple_plausible_clusters_remain_unknown():
 obj,lidar,rgb=measurements(sensor_points(True))
 result=localize([obj],lidar,rgb,Radar(),Transform())
 assert result['objects'][0]['status']=='UNKNOWN'
 assert result['objects'][0]['reason']=='MULTIPLE_PLAUSIBLE_CLUSTERS'
def test_sensor_frame_mismatch_rejected():
 obj,lidar,rgb=measurements(sensor_points());lidar.frame=4
 with pytest.raises(ValueError,match='frame mismatch'):localize([obj],lidar,rgb,Radar(),Transform())

def test_radar_must_project_inside_same_exclusive_box():
 import math
 obj,lidar,rgb=measurements(sensor_points())
 obj.bbox_xyxy_norm=(.49,.35,.51,.6)
 def point(y):
  x=10.;z=.5;depth=math.sqrt(x*x+y*y+z*z)
  return SimpleNamespace(depth=depth,azimuth=math.atan2(y,x),altitude=math.atan2(z,math.hypot(x,y)))
 r=Radar([point(0),point(.7)])
 out=localize([obj],lidar,rgb,r,Transform())['objects'][0]
 assert out['status']=='LOCATED_UNVALIDATED'
 assert out['radar_point_indices']==[0]
