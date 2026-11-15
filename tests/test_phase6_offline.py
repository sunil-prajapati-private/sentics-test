import tempfile,unittest,os
from onprem.app.persistence import OnPremStore
from onprem.app.execution import JobCommand,RobotScheduler
class OfflineRecoveryTests(unittest.TestCase):
 def enrolled(self,s): s.enroll('site-1','robot-1','cell-1','A,B,C','now')
 def test_queue_reconstructed_after_restart(self):
  fd,path=tempfile.mkstemp();os.close(fd)
  try:
   first=OnPremStore(path);self.enrolled(first); a=RobotScheduler(first);a.receive(JobCommand('m1','j1','robot-1','A','B'));a.receive(JobCommand('m2','j2','robot-1','B','C'))
   second=RobotScheduler(OnPremStore(path));self.assertEqual(second.run_next('robot-1'),'j1')
  finally: os.unlink(path)
 def test_running_job_fails_safe_after_restart(self):
  fd,path=tempfile.mkstemp();os.close(fd)
  try:
   first=OnPremStore(path);self.enrolled(first);a=RobotScheduler(first);a.receive(JobCommand('m1','j1','robot-1','A','B'));a.run_next('robot-1')
   second=RobotScheduler(OnPremStore(path));self.assertTrue(any(e.get('reason')=='restart_recovery_ambiguous' for e in second.events));self.assertIsNone(second.run_next('robot-1'))
  finally: os.unlink(path)
 def test_duplicate_replay_after_restart_is_ignored(self):
  fd,path=tempfile.mkstemp();os.close(fd)
  try:
   first=OnPremStore(path);self.enrolled(first);a=RobotScheduler(first);a.receive(JobCommand('m1','j1','robot-1','A','B'))
   second=RobotScheduler(OnPremStore(path));self.assertIsNone(second.receive(JobCommand('m1','j1','robot-1','A','B')));self.assertEqual(second.store.db.execute('select count(*) from robot_queue').fetchone()[0],1)
  finally: os.unlink(path)
if __name__=='__main__':unittest.main()
