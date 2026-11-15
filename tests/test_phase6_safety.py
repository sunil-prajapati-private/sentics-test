import unittest
from onprem.app.safety import SafetyController
from onprem.app.execution import JobCommand
class SafetyTests(unittest.TestCase):
 def setUp(self):
  self.s=SafetyController(); self.s.store.enroll('site-1','robot-1','cell-1','A,B,C','now'); self.s.store.enroll('site-1','robot-2','cell-2','C,D,E','now')
 def test_enter_pauses_only_active_robot_and_repeated_is_safe(self):
  self.s.receive(JobCommand('m1','j1','robot-1','A','B')); self.s.run_next('robot-1'); self.assertEqual(self.s.person_entered('cell-1','e1')['state'],'paused'); self.assertIsNone(self.s.person_entered('cell-1','e2')); self.assertEqual(self.s.active['robot-1'],'j1')
 def test_unsafe_cell_blocks_new_work_and_clear_resumes(self):
  self.s.person_entered('cell-1','e1'); self.s.receive(JobCommand('m1','j1','robot-1','A','B')); self.assertIsNone(self.s.run_next('robot-1')); self.assertEqual(self.s.person_left('cell-1','e2')['state'],'clear'); self.assertEqual(self.s.run_next('robot-1'),'j1')
 def test_cells_are_independent_and_leave_is_idempotent(self):
  self.s.person_entered('cell-1','e1'); self.s.receive(JobCommand('m2','j2','robot-2','C','D')); self.assertEqual(self.s.run_next('robot-2'),'j2'); self.assertIsNone(self.s.person_left('cell-2','x'))
if __name__=='__main__': unittest.main()
