import unittest
from onprem.app.execution import JobCommand,RobotScheduler
class Phase5Tests(unittest.TestCase):
 def test_rejects_invalid_and_deduplicates(self):
  s=RobotScheduler(); s.store.enroll('site-1','robot-1','cell-1','A,B,C','now'); s.store.enroll('site-1','robot-2','cell-2','C,D,E','now'); s.store.enroll('site-1','robot-1','cell-1','A,B,C','now'); s.store.enroll('site-1','robot-2','cell-2','C,D,E','now'); self.assertEqual(s.receive(JobCommand('m1','j1','robot-1','A','E'))['state'],'rejected'); self.assertIsNotNone(s.receive(JobCommand('m2','j2','robot-1','A','B'))); self.assertIsNone(s.receive(JobCommand('m2','j2','robot-1','A','B')))
 def test_one_active_job_per_robot(self):
  s=RobotScheduler(); s.store.enroll('site-1','robot-1','cell-1','A,B,C','now'); s.store.enroll('site-1','robot-2','cell-2','C,D,E','now'); s.receive(JobCommand('m1','j1','robot-1','A','B')); s.receive(JobCommand('m2','j2','robot-1','B','C')); s.run_next('robot-1'); self.assertIsNone(s.run_next('robot-1')); s.finish('robot-1'); self.assertEqual(s.run_next('robot-1'),'j2')
 def test_robots_run_concurrently(self):
  s=RobotScheduler(); s.store.enroll('site-1','robot-1','cell-1','A,B,C','now'); s.store.enroll('site-1','robot-2','cell-2','C,D,E','now'); s.receive(JobCommand('m1','j1','robot-1','A','B')); s.receive(JobCommand('m2','j2','robot-2','C','D')); self.assertEqual(s.run_next('robot-1'),'j1'); self.assertEqual(s.run_next('robot-2'),'j2')
 def test_deterministic_failure(self):
  s=RobotScheduler(); s.store.enroll('site-1','robot-1','cell-1','A,B,C','now'); s.store.enroll('site-1','robot-2','cell-2','C,D,E','now'); s.receive(JobCommand('m1','j1','robot-1','A','B')); s.run_next('robot-1'); self.assertEqual(s.finish('robot-1','always_fail')['state'],'failed')
if __name__=='__main__':unittest.main()
