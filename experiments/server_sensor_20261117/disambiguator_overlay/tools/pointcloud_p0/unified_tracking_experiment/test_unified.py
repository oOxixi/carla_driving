import unittest
from tools.pointcloud_p0.unified_tracking_experiment.tracker import UnifiedTracker,Observation

def o(f,ch='formal',x=0,box=(.1,.1,.2,.2),ids=(1,2,3),cls='car',valid=True,unresolved=False,id=None):return Observation(id or ch+str(f),ch,cls,.9,box,f*.05,(x,0,0) if valid else None,ids if valid else (),unresolved)
class Tests(unittest.TestCase):
 def test_bidirectional_channel_migration_requires_3d(self):
  t=UnifiedTracker();a=t.step(1,.05,[o(1)])[0];b=t.step(2,.1,[o(2,'auxiliary',.03)])[0];c=t.step(3,.15,[o(3,'formal',.06)])[0];self.assertEqual([a['track_id'],b['track_id'],c['track_id']],['T-0001']*3);self.assertEqual(c['migrations'],2);self.assertEqual(c['state'],'CONFIRMED_TRACK');self.assertFalse(c['may_enter_follow'])
 def test_visual_only_cannot_switch_channel(self):
  t=UnifiedTracker();t.step(1,.05,[o(1)]);rows=t.step(2,.1,[o(2,'auxiliary',valid=False)]);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['state'],'AMBIGUOUS');self.assertEqual(rows[0]['channel'],'formal');self.assertIsNone(rows[0]['position_world_surface_proxy'])
 def test_conflicting_observations_not_forced(self):
  t=UnifiedTracker();t.step(1,.05,[o(1)]);rows=t.step(2,.1,[o(2,id='a'),o(2,'auxiliary',id='b',ids=(4,5,6))]);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['state'],'AMBIGUOUS');self.assertIsNone(rows[0]['observation_id'])
 def test_duplicates_or_unresolved_cannot_confirm(self):
  t=UnifiedTracker();rows=t.step(1,.05,[o(1,id='a'),o(1,'auxiliary',ids=(3,4,5),id='b',box=(.3,.1,.4,.2))]);self.assertTrue(all(x['state']=='AMBIGUOUS' for x in rows));self.assertTrue(all(x['position_world_surface_proxy'] is None for x in rows))
 def test_lost_has_no_stale_position(self):
  t=UnifiedTracker();t.step(1,.05,[o(1)]);t.step(2,.1,[]);t.step(3,.15,[]);r=t.step(4,.2,[])[0];self.assertEqual(r['state'],'LOST');self.assertIsNone(r['position_world_surface_proxy']);self.assertIsNone(r['velocity_world_surface_proxy'])
 def test_nearby_disjoint_boxes_do_not_compete(self):
  t=UnifiedTracker();a=o(1,box=(.40,.1,.44,.2),id='a');b=o(1,'auxiliary',box=(.46,.1,.50,.2),ids=(4,5,6),id='b');t.step(1,.05,[a,b]);rows=t.step(2,.1,[o(2,box=(.40,.1,.44,.2),id='c'),o(2,'auxiliary',box=(.46,.1,.50,.2),ids=(4,5,6),id='d')]);self.assertEqual([x['state'] for x in rows],['TENTATIVE_3D','TENTATIVE_3D']);self.assertEqual([x['observation_id'] for x in rows],['c','d'])
 def test_velocity_requires_two_3d_measurements(self):
  t=UnifiedTracker();a=t.step(1,.05,[o(1)])[0];self.assertIsNone(a['velocity_world_surface_proxy']);b=t.step(2,.1,[o(2,x=.03)])[0];self.assertIsNotNone(b['velocity_world_surface_proxy'])
 def test_freshness_and_no_observation_reuse(self):
  t=UnifiedTracker();t.step(1,.05,[o(1)]);
  with self.assertRaises(ValueError):t.step(1,.05,[o(1)])
  with self.assertRaises(ValueError):t.step(2,.1,[o(2,id='x'),o(2,id='x')])
if __name__=='__main__':unittest.main()
