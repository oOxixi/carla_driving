import math
from types import SimpleNamespace
import carla
from integration.target_lane_association import associate,build_follow_candidates

class Waypoint:
 def __init__(self,s,lane):
  theta=s/30.;side={'CURRENT':0.,'LEFT':-3.5,'RIGHT':3.5}[lane]
  x=30*math.sin(theta)-side*math.sin(theta)
  y=30*(1-math.cos(theta))+side*math.cos(theta)
  self.s=s;self.name=lane;self.road_id=1;self.lane_id={'CURRENT':-2,'LEFT':-1,'RIGHT':-3}[lane]
  self.lane_width=3.5;self.lane_type=carla.LaneType.Driving;self.is_junction=False
  self.transform=carla.Transform(carla.Location(x=x,y=y,z=0),carla.Rotation(yaw=math.degrees(theta)))
 def next(self,d):return [self.graph[(self.name,round(self.s+d))]] if (self.name,round(self.s+d)) in self.graph else []
 def previous(self,d):return [self.graph[(self.name,round(self.s-d))]] if (self.name,round(self.s-d)) in self.graph else []
 def get_left_lane(self):return self.graph.get(({'CURRENT':'LEFT','RIGHT':'CURRENT'}.get(self.name),self.s))
 def get_right_lane(self):return self.graph.get(({'CURRENT':'RIGHT','LEFT':'CURRENT'}.get(self.name),self.s))
class Map:
 def __init__(self):
  self.graph={(lane,s):Waypoint(s,lane) for lane in ('CURRENT','LEFT','RIGHT') for s in range(-20,82,2)}
  for wp in self.graph.values():wp.graph=self.graph
 def get_waypoint(self,loc,**kwargs):
  return min(self.graph.values(),key=lambda w:math.hypot(w.transform.location.x-loc.x,w.transform.location.y-loc.y))
 def loc(self,lane,s):return self.graph[(lane,s)].transform.location

def test_curved_road_matches_lane_and_longitudinal():
 m=Map();ego=m.loc('CURRENT',0)
 for name in ('CURRENT','LEFT','RIGHT'):
  r=associate(m,ego,m.loc(name,24))
  assert (r['lane_relation'],r['longitudinal_relation'])==(name,'AHEAD')
  assert abs(r['delta_s_m']-24)<0.01
 r=associate(m,ego,m.loc('CURRENT',-8))
 assert r['lane_relation']=='CURRENT' and r['longitudinal_relation']=='BEHIND'
def test_lane_boundary_and_junction_remain_unknown():
 m=Map();e=m.loc('CURRENT',0)
 x=m.loc('CURRENT',20);y=m.loc('LEFT',20)
 boundary=carla.Location(x=(x.x+y.x)/2,y=(x.y+y.y)/2,z=0)
 assert associate(m,e,boundary)['lane_relation']=='UNKNOWN'
 m.graph[('CURRENT',20)].is_junction=True
 assert associate(m,e,m.loc('CURRENT',20))['reason']=='JUNCTION'
def test_no_unsafe_candidate_from_unknown_or_adjacent():
 items=[{'id':'good','class':'car','distance_m':20,'lane_relation':'CURRENT','longitudinal_relation':'AHEAD','same_lane':True},
        {'id':'side','class':'car','distance_m':10,'lane_relation':'LEFT','longitudinal_relation':'AHEAD','same_lane':False},
        {'id':'unknown','class':'car','distance_m':None,'lane_relation':'UNKNOWN','longitudinal_relation':'UNKNOWN','same_lane':None}]
 items.extend([{'id':'nan','class':'car','distance_m':float('nan'),'lane_relation':'CURRENT','longitudinal_relation':'AHEAD','same_lane':True}, {'id':'negative','class':'car','distance_m':-1,'lane_relation':'CURRENT','longitudinal_relation':'AHEAD','same_lane':True}])
 assert build_follow_candidates(items)==['good']

def test_road_fork_does_not_extrapolate_into_unknown_path():
 m=Map();ego=m.loc('CURRENT',0)
 fork=m.graph[('CURRENT',8)]
 fork.next=lambda d:[m.graph[('CURRENT',10)],m.graph[('CURRENT',12)]]
 result=associate(m,ego,m.loc('CURRENT',20))
 assert result['lane_relation']=='UNKNOWN'
 assert result['reason']=='OUTSIDE_UNAMBIGUOUS_PATH'
