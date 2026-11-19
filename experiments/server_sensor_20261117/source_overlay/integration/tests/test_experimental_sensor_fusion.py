import numpy as np
from types import SimpleNamespace as NS
from integration.contracts import DetectedObject
from integration.experimental_sensor_fusion import ShadowSensorFusion

class Transform:
    def get_matrix(self): return np.eye(4).tolist()
    def get_inverse_matrix(self): return np.eye(4).tolist()
class Radar(list): pass

def sensors(frame=1,radar_points=True,lidar_points=True):
    t=frame*.05;tf=Transform();rgb=NS(frame=frame,timestamp=t,transform=tf,width=200,height=100)
    arr=np.array([[20.1,.05,0,1]],dtype=np.float32) if lidar_points else np.empty((0,4),dtype=np.float32)
    lidar=NS(frame=frame,timestamp=t,transform=tf,raw_data=arr.tobytes())
    radar=Radar([NS(depth=20.,azimuth=0.,altitude=0.,velocity=-2.)] if radar_points else [])
    radar.frame=frame;radar.timestamp=t;radar.transform=tf
    return lidar,rgb,radar,tf

def car(track,box=(.4,.4,.6,.6)):
    return DetectedObject(2,'car',.9,box,track_id=track)

def test_requires_three_consecutive_cross_sensor_observations():
    f=ShadowSensorFusion();o=car('one')
    for n in (1,2):
        lidar,rgb,radar,ego=sensors(n);r=f.update([o],lidar,rgb,radar,ego,90)
        assert r[0]['status']=='TEMPORAL_PENDING' and r[0]['position_m'] is None
    lidar,rgb,radar,ego=sensors(3);r=f.update([o],lidar,rgb,radar,ego,90)[0]
    assert r['status']=='FUSED_UNVALIDATED' and 19.9<r['distance_m']<20.2
    assert r['radial_velocity_mps']==-2 and r['lane_relation']=='UNKNOWN'

def test_overlap_and_single_sensor_never_make_a_position():
    f=ShadowSensorFusion();a,b=car('a'),car('b')
    for n in (1,2,3):
        lidar,rgb,radar,ego=sensors(n);r=f.update([a,b],lidar,rgb,radar,ego,90)
        assert all(v['position_m'] is None and v['radar_ambiguous']==1 for v in r)
    for n in (4,5,6):
        lidar,rgb,radar,ego=sensors(n,lidar_points=False);r=f.update([a],lidar,rgb,radar,ego,90)
        assert r[0]['position_m'] is None

def test_bad_sync_and_frame_gap_reset_evidence():
    f=ShadowSensorFusion();a=car('a')
    lidar,rgb,radar,ego=sensors(1);f.update([a],lidar,rgb,radar,ego,90)
    lidar,rgb,radar,ego=sensors(2);radar.timestamp+=.1
    assert f.update([a],lidar,rgb,radar,ego,90)[0]['status']=='UNSYNCED'
    lidar,rgb,radar,ego=sensors(3)
    assert f.update([a],lidar,rgb,radar,ego,90)[0]['streak']==1
    lidar,rgb,radar,ego=sensors(5)
    assert f.update([a],lidar,rgb,radar,ego,90)[0]['streak']==1

def test_duplicate_track_ids_do_not_accumulate():
    f=ShadowSensorFusion();lidar,rgb,radar,ego=sensors()
    r=f.update([car('a'),car('a')],lidar,rgb,radar,ego,90)
    assert all(x['status']=='DUPLICATE_TRACK' for x in r)
