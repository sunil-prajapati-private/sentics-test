from dataclasses import dataclass
from shared.contracts import CAPABILITIES, JobStatus, validate_capability
from .persistence import OnPremStore

def locked(method):
 def wrapper(self, *args, **kwargs):
  with self.store.db_lock:
   return method(self, *args, **kwargs)
 return wrapper

@dataclass
class JobCommand:
 message_id:str; job_id:str; robot_id:str; source_station:str; destination_station:str; site_id:str='site-1'; failure_mode:str|None=None

class RobotScheduler:
 def __init__(self,store=None):
  self.store=store or OnPremStore(); self.events=[]; self.active={}
  # A persisted running job has an ambiguous external effect after a crash.
  # Fail it safely rather than execute the same action twice.
  for job_id,_ in self.store.recover_interrupted(): self._event(job_id,JobStatus.FAILED,'restart_recovery_ambiguous')

 def _event(self,job_id,state,reason=None):
  event={'job_id':job_id,'state':state}
  if reason:event['reason']=reason
  self.events.append(event); return event
 @locked
 def receive(self,cmd:JobCommand,now='now'):
  if cmd.site_id!='site-1': return self._event(cmd.job_id,JobStatus.REJECTED,'unknown_site')
  try: cell,stations=CAPABILITIES[cmd.robot_id]; validate_capability(cmd.robot_id,cell,cmd.source_station,cmd.destination_station)
  except (KeyError,ValueError): return self._event(cmd.job_id,JobStatus.REJECTED,'invalid_robot_or_station')
  if not self.store.db.execute("SELECT 1 FROM enrollments WHERE site_id=? AND robot_id=? AND state='approved'",(cmd.site_id,cmd.robot_id)).fetchone(): return self._event(cmd.job_id,JobStatus.REJECTED,'robot_not_enrolled')
  if not self.store.record_command(cmd.message_id,cmd.job_id,now): return None
  self._event(cmd.job_id,JobStatus.RECEIVED)
  self.store.db.execute('INSERT OR IGNORE INTO robot_queue(robot_id,job_id,status,failure_mode) VALUES(?,?,?,?)',(cmd.robot_id,cmd.job_id,'queued',cmd.failure_mode)); self.store.db.commit()
  return self._event(cmd.job_id,JobStatus.QUEUED)
 @locked
 def run_next(self,robot_id,now='now'):
  if robot_id in self.active:return None
  row=self.store.db.execute("SELECT job_id FROM robot_queue WHERE robot_id=? AND status='queued' ORDER BY position LIMIT 1",(robot_id,)).fetchone()
  if not row:return None
  job_id=row[0]; self.active[robot_id]=job_id; existing=self.store.db.execute("SELECT state FROM job_executions WHERE job_id=?",(job_id,)).fetchone(); self.store.db.execute("UPDATE robot_queue SET status='running' WHERE job_id=?",(job_id,)); self.store.db.execute("UPDATE job_executions SET state='running',started_at=? WHERE job_id=?",(now,job_id)); self.store.db.commit(); self.store.claim_execution(job_id,job_id+':1')
  if not existing or existing[0] != 'retrying': self._event(job_id,JobStatus.RUNNING)
  return job_id
 @locked
 def cancel(self, job_id):
  row=self.store.db.execute("SELECT robot_id,status FROM robot_queue WHERE job_id=?",(job_id,)).fetchone()
  if not row or row[1] != 'queued': return None
  self.store.db.execute("UPDATE robot_queue SET status='cancelled' WHERE job_id=?",(job_id,)); self.store.db.commit()
  return self._event(job_id,JobStatus.CANCELLED,'operator_cancelled')
 @locked
 def retry_active(self, robot_id):
  job_id=self.active.pop(robot_id,None)
  if not job_id: return False
  row=self.store.db.execute("SELECT retry_count FROM job_executions WHERE job_id=?",(job_id,)).fetchone()
  retries=(row[0] if row else 0)+1
  self.store.db.execute("UPDATE robot_queue SET status='queued' WHERE job_id=?",(job_id,))
  self.store.db.execute("UPDATE job_executions SET state='retrying',retry_count=? WHERE job_id=?",(retries,job_id)); self.store.db.commit()
  return True
 @locked
 def finish(self,robot_id,failure_mode=None):
  job_id=self.active.pop(robot_id,None)
  if not job_id:return None
  failed=failure_mode in ('always_fail','fail_once','timeout')
  state=JobStatus.FAILED if failed else JobStatus.DONE; reason='deterministic_failure' if failed else None
  self.store.db.execute("UPDATE robot_queue SET status=? WHERE job_id=?",('failed' if failed else 'done',job_id)); self.store.db.execute("UPDATE job_executions SET state=? WHERE job_id=?",('failed' if failed else 'done',job_id)); self.store.db.commit()
  return self._event(job_id,state,reason)
