import sqlite3
SCHEMA='''CREATE TABLE IF NOT EXISTS received_commands(message_id TEXT PRIMARY KEY,job_id TEXT NOT NULL,received_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS job_executions(job_id TEXT PRIMARY KEY,execution_key TEXT UNIQUE NOT NULL,state TEXT NOT NULL,started_at TEXT,finished_at TEXT); CREATE TABLE IF NOT EXISTS robot_state(site_id TEXT NOT NULL,robot_id TEXT NOT NULL,state TEXT NOT NULL,cell_id TEXT NOT NULL,PRIMARY KEY(site_id,robot_id)); CREATE TABLE IF NOT EXISTS robot_queue(position INTEGER PRIMARY KEY AUTOINCREMENT,robot_id TEXT NOT NULL,job_id TEXT UNIQUE NOT NULL,status TEXT NOT NULL); CREATE TABLE IF NOT EXISTS cell_safety_state(cell_id TEXT PRIMARY KEY,occupied INTEGER NOT NULL,event_id TEXT UNIQUE NOT NULL,updated_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS enrollments(site_id TEXT NOT NULL,robot_id TEXT NOT NULL,cell_id TEXT NOT NULL,stations TEXT NOT NULL,state TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(site_id,robot_id)); CREATE TABLE IF NOT EXISTS processed_message_ids(message_id TEXT PRIMARY KEY,processed_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS outbound_events(message_id TEXT PRIMARY KEY,payload TEXT NOT NULL,published_at TEXT);'''
class OnPremStore:
 def __init__(self,path=':memory:'): self.db=sqlite3.connect(path); self.db.executescript(SCHEMA); self.db.commit()
 def record_command(self,message_id,job_id,now):
  try:self.db.execute('INSERT INTO received_commands VALUES(?,?,?)',(message_id,job_id,now));self.db.commit();return True
  except sqlite3.IntegrityError:return False
 def claim_execution(self,job_id,key):
  try:self.db.execute('INSERT INTO job_executions(job_id,execution_key,state) VALUES(?,?,?)',(job_id,key,'claimed'));self.db.commit();return True
  except sqlite3.IntegrityError:return False
 def enroll(self,site,robot,cell,stations,now): self.db.execute('INSERT OR REPLACE INTO enrollments VALUES(?,?,?,?,?,?)',(site,robot,cell,stations,'approved',now));self.db.commit()
 def queued_jobs(self,robot_id=None):
  if robot_id: return [r[0] for r in self.db.execute("SELECT job_id FROM robot_queue WHERE robot_id=? AND status='queued' ORDER BY position",(robot_id,))]
  return [(r[0],r[1]) for r in self.db.execute("SELECT job_id,robot_id FROM robot_queue WHERE status='queued' ORDER BY position")]
 def recover_interrupted(self,reason='restart_recovery_ambiguous'):
  rows=self.db.execute("SELECT job_id,robot_id FROM robot_queue WHERE status='running'").fetchall()
  with self.db:
   for job_id,_ in rows:
    self.db.execute("UPDATE robot_queue SET status='failed' WHERE job_id=?",(job_id,))
    self.db.execute("UPDATE job_executions SET state='failed',finished_at=? WHERE job_id=?",(reason,job_id))
  return rows
