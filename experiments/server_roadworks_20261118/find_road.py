import math
import carla

c = carla.Client('127.0.0.1', 24560)
c.set_timeout(20)
w = c.get_world()
m = w.get_map()
print(c.get_server_version(), m.name)
print([b.id for b in w.get_blueprint_library() if any(s in b.id for s in ('century','gazelle','omafiets','construction','streetbarrier','lincoln','trafficcone','dirtdebris'))])
def same(a,b):
    return b and b.lane_type == carla.LaneType.Driving and abs((b.transform.rotation.yaw-a.transform.rotation.yaw+180)%360-180)<25
def fits(a):
    if a.is_junction or not same(a,a.get_left_lane()):
        return None
    row=[a]
    for step in range(1,16):
        bs=row[-1].next(4)
        if len(bs)!=1:
            break
        b=bs[0]
        if b.is_junction or not same(a,b) or not same(b,b.get_left_lane()):
            break
        row.append(b)
    if len(row)<9:
        return None
    end=row[-1]
    z=max(x.transform.location.z for x in row)-min(x.transform.location.z for x in row)
    return (len(row), sum(bool(same(x,x.get_right_lane())) for x in row), -z, a.road_id,a.lane_id,round(a.s,1),[round(v,1) for v in (a.transform.location.x,a.transform.location.y,a.transform.location.z,a.transform.rotation.yaw)],str(a.left_lane_marking.type))
rows = [r for a in m.generate_waypoints(4) if (r:=fits(a))]
for road in sorted(set(x[3] for x in rows)):
    for r in sorted((x for x in rows if x[3]==road),reverse=True)[:3]:
        print(r)
