import unittest
from request_guard import adapt_or_block
class TestGuard(unittest.TestCase):
 def test_unknown_is_blocked_without_mutation(self):
  req={'targets':[{'target_id':'a','distance_m':None}], 'target_grounding':{'status':'AMBIGUOUS'}}
  x,status=adapt_or_block(req)
  self.assertIsNone(x);self.assertEqual(status['status'],'BLOCKED_UNKNOWN_DISTANCE')
  self.assertIsNone(req['targets'][0]['distance_m'])
 def test_known_zero_is_not_unknown(self):
  req={'targets':[{'target_id':'a','distance_m':0.0}], 'target_grounding':{'status':'AMBIGUOUS'}}
  x,status=adapt_or_block(req)
  self.assertEqual(status['status'],'ALLOWED_KNOWN_DISTANCE');self.assertEqual(x['targets'][0]['distance_m'],0)
  self.assertNotIn('target_grounding',x);self.assertIn('target_grounding',req)
 def test_mixed_unknown_blocks(self):
  x,status=adapt_or_block({'targets':[{'target_id':'a','distance_m':10.0},{'target_id':'b','distance_m':None}]})
  self.assertIsNone(x);self.assertEqual(status['unknown_target_ids'],['b'])
if __name__=='__main__':unittest.main()
