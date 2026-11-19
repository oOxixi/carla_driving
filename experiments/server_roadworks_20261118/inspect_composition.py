import json
from math import dist
import carla
c=carla.Client('127.0.0.1',24560)
c.set_timeout(90)
w=c.load_world('Town10HD_Opt')
m=w.get_map()
wp=m.get_waypoint_xodr(20,-2,15)
for i in range(0,5):
    if not wp:
        break
    print('lane',i,wp.lane_id,wp.lane_type,wp.lane_width,wp.transform.location)
    wp=wp.get_right_lane()
state=json.load(open('boulevard_f90_capture.json'))['source']
loc=state['camera_location']
for o in w.get_environment_objects(carla.CityObjectLabel.Any):
    b=o.bounding_box
    a=b.location
    if dist(loc,[a.x,a.y,a.z])<18:
        print(o.id,o.type,o.name,[round(x,2) for x in (a.x,a.y,a.z,b.extent.x,b.extent.y,b.extent.z)])
