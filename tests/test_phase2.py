import unittest
from shared.contracts import Envelope,JobStatus,validate_capability,validate_transition
from cloud.app.persistence import CloudStore
from onprem.app.persistence import OnPremStore
class Phase2Tests(unittest.TestCase):
 def test_transitions_and_rejections(self):
  validate_transition(JobStatus.PENDING,JobStatus.RECEIVED)
  with self.assertRaises(ValueError): validate_transition(JobStatus.DONE,JobStatus.RUNNING)
 def test_capabilities(self):
  validate_capability('robot-1','cell-1','A','B'); validate_capability('robot-2','cell-2','C','E')
  with self.assertRaises(ValueError): validate_capability('robot-1','cell-1','A','E')
 def test_envelope(self): self.assertEqual(Envelope('1','m','job.command','cloud','site','now',{}).as_dict()['message_id'],'m')
 def test_cloud_persistence_and_idempotent_status(self):
  s=CloudStore();s.create_job('j','site','robot-1','A','B','t');self.assertTrue(s.transition('j','received',None,'t2','m1'));self.assertFalse(s.transition('j','received',None,'t2','m1'))
 def test_onprem_dedup_and_execution_claim(self):
  s=OnPremStore();self.assertTrue(s.record_command('m','j','t'));self.assertFalse(s.record_command('m','j','t'));self.assertTrue(s.claim_execution('j','j:1'));self.assertFalse(s.claim_execution('j','j:1'))
if __name__=='__main__': unittest.main()
