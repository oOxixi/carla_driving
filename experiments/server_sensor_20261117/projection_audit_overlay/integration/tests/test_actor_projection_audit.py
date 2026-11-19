from types import SimpleNamespace as NS
from integration.actor_projection_audit import projected_actor_aliases
from integration.contracts import DetectedObject, PerceptionFrame


def actor(x, y):
 vertices=[NS(x=x+dx,y=y+dy,z=dz) for dx in (-1,1) for dy in (-.5,.5) for dz in (-.5,.5)]
 return NS(is_alive=True,bounding_box=NS(get_world_vertices=lambda _:vertices),get_transform=lambda:None)


def camera(frame=10):
 return NS(frame=frame,width=800,height=450,transform=NS(get_inverse_matrix=lambda:[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]))


def detect(track='C-1',box=(.47,.44,.53,.56)):
 return DetectedObject(2,'car',.9,box,None,track)


def test_unique_projection_matches_without_changing_scene():
 scene=PerceptionFrame(10,.5,detected_objects=(detect(),))
 assert projected_actor_aliases(scene,camera(),[(actor(10,0),{'type':'vehicle','actor_id':'lead'})],90,10)=={'C-1':'lead'}
 assert scene.detected_objects[0].track_id=='C-1'


def test_overlapping_actor_projections_are_not_assigned():
 scene=PerceptionFrame(10,.5,detected_objects=(detect(),))
 assert projected_actor_aliases(scene,camera(),[(actor(10,0),{'type':'vehicle','actor_id':'lead'}),(actor(20,0),{'type':'vehicle','actor_id':'behind'})],90,10)=={}


def test_wrong_frame_and_missing_calibration_are_not_assigned():
 scene=PerceptionFrame(10,.5,detected_objects=(detect(),));actors=[(actor(10,0),{'type':'vehicle','actor_id':'lead'})]
 assert projected_actor_aliases(scene,camera(11),actors,90,10)=={}
 assert projected_actor_aliases(scene,camera(),actors,None,10)=={}


def test_two_tracks_cannot_claim_same_actor():
 scene=PerceptionFrame(10,.5,detected_objects=(detect('A'),detect('B')))
 assert projected_actor_aliases(scene,camera(),[(actor(10,0),{'type':'vehicle','actor_id':'lead'})],90,10)=={}


def test_nearby_but_different_lane_tracks_do_not_bind_to_lead():
 scene=PerceptionFrame(10,.5,detected_objects=(detect('side',(.62,.44,.68,.56)),))
 actors=[(actor(10,0),{'type':'vehicle','actor_id':'lead'}),(actor(10,3),{'type':'vehicle','actor_id':'adjacent'})]
 assert projected_actor_aliases(scene,camera(),actors,90,10)=={'side':'adjacent'}


def test_stale_world_snapshot_is_not_assigned():
 scene=PerceptionFrame(10,.5,detected_objects=(detect(),))
 assert projected_actor_aliases(scene,camera(),[(actor(10,0),{'type':'vehicle','actor_id':'lead'})],90,11)=={}
