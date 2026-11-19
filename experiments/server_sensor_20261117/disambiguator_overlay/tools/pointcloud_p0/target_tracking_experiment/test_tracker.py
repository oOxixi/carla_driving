import unittest
from tools.pointcloud_p0.target_tracking_experiment.tracker import Observation,TargetTracker

def obs(frame,channel='formal',x=0.,bbox=(.1,.1,.2,.2),points=(1,2,3),unresolved=False,cls='car',has3d=True,oid=None):
 return Observation(oid or channel+str(frame),channel,cls,.9,bbox,frame*.05,(x,0.,0.) if has3d else None,points if has3d else (),unresolved)
class TrackingTest(unittest.TestCase):
 def test_three_in_five_and_recovery(self):
  t=TargetTracker()
  self.assertEqual(t.step(1,.05,[obs(1)])[0]['state'],'TENTATIVE_3D')
  self.assertEqual(t.step(2,.10,[obs(2,x=.02)])[0]['state'],'TENTATIVE_3D')
  s=t.step(3,.15,[obs(3,x=.04)])[0];self.assertEqual(s['state'],'CONFIRMED_TRACK');self.assertFalse(s['may_enter_follow'])
  s=t.step(4,.20,[])[0];self.assertEqual(s['state'],'AMBIGUOUS');self.assertIsNone(s['position_world_surface_proxy'])
  self.assertEqual(t.step(5,.25,[obs(5,x=.06)])[0]['state'],'CONFIRMED_TRACK')
 def test_missing_reaches_lost_and_hides_stale_data(self):
  t=TargetTracker();t.step(1,.05,[obs(1)]);t.step(2,.10,[]);t.step(3,.15,[]);s=t.step(4,.20,[])[0];self.assertEqual(s['state'],'LOST');self.assertIsNone(s['position_world_surface_proxy'])
 def test_visual_only_never_confirms(self):
  t=TargetTracker()
  for i in range(1,7):self.assertEqual(t.step(i,i*.05,[obs(i,has3d=False)])[0]['state'],'VISUAL_ONLY')
 def test_duplicate_points_and_unresolved_block_both(self):
  t=TargetTracker();rows=t.step(1,.05,[obs(1,'formal'),obs(1,'auxiliary',points=(3,4,5))]);self.assertTrue(all(x['state']=='AMBIGUOUS' for x in rows));self.assertTrue(all(x['position_world_surface_proxy'] is None for x in rows))
  t=TargetTracker();rows=t.step(1,.05,[obs(1,unresolved=True)]);self.assertEqual(rows[0]['state'],'AMBIGUOUS')
 def test_competing_associations_do_not_force_id(self):
  t=TargetTracker();t.step(1,.05,[obs(1,bbox=(.1,.1,.2,.2),oid='a'),obs(1,bbox=(.25,.1,.35,.2),oid='b',points=(4,5,6))]);rows=t.step(2,.10,[obs(2,bbox=(.175,.1,.275,.2),oid='c'),obs(2,bbox=(.175,.1,.275,.2),oid='d',points=(4,5,6))]);self.assertEqual(len(rows),2);self.assertTrue(all(x['state']=='AMBIGUOUS' and x['matched_observation_id'] is None for x in rows))
 def test_out_of_order_rejected(self):
  t=TargetTracker();t.step(1,.05,[obs(1)])
  with self.assertRaises(ValueError):t.step(1,.05,[obs(1)])
 def test_failed_gate_is_not_silently_new_track(self):
  t=TargetTracker();t.step(1,.05,[obs(1)]);s=t.step(2,.10,[obs(2,x=20.)]);self.assertEqual(len(s),1);self.assertEqual(s[0]['state'],'AMBIGUOUS')
if __name__=='__main__':unittest.main()
