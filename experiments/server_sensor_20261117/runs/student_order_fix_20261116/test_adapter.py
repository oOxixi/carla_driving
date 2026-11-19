import unittest
from order_adapter import canonical_request
class TestCanonical(unittest.TestCase):
 def test_permuted_candidates_produce_same_student_input(self):
  targets=[{'target_id':'b','distance_m':20},{'target_id':'a','distance_m':10}]
  a={'targets':targets};b={'targets':targets[::-1]}
  self.assertEqual(canonical_request(a),canonical_request(b));self.assertEqual(a['targets'][0]['target_id'],'b')
 def test_missing_distance_is_refused(self):
  with self.assertRaises(ValueError):canonical_request({'targets':[{'target_id':'a','distance_m':None}]})
 def test_swapped_ids_keep_same_distance_order(self):
  a={'targets':[{'target_id':'a','distance_m':10.0},{'target_id':'b','distance_m':20.0}]}
  b={'targets':[{'target_id':'b','distance_m':10.0},{'target_id':'a','distance_m':20.0}]}
  self.assertEqual([t['distance_m'] for t in canonical_request(a)['targets']],[t['distance_m'] for t in canonical_request(b)['targets']])
 def test_ambiguous_distance_is_refused(self):
  with self.assertRaises(ValueError):canonical_request({'targets':[{'target_id':'a','distance_m':10},{'target_id':'b','distance_m':10.5}]})
 def test_duplicate_id_is_refused(self):
  with self.assertRaises(ValueError):canonical_request({'targets':[{'target_id':'a','distance_m':1},{'target_id':'a','distance_m':2}]})
if __name__=='__main__':unittest.main()
