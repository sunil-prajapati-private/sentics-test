import sqlite3
import threading
from pathlib import Path
SCHEMA='''CREATE TABLE IF NOT EXISTS received_commands(message_id TEXT PRIMARY KEY,job_id TEXT NOT NULL,received_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS job_executions(job_id TEXT PRIMARY KEY,execution_key TEXT UNIQUE NOT NULL,state TEXT NOT NULL,started_at TEXT,finished_at TEXT,retry_count INTEGER NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS robot_state(site_id TEXT NOT NULL,robot_id TEXT NOT NULL,state TEXT NOT NULL,cell_id TEXT NOT NULL,state_reason TEXT,last_seen TEXT,PRIMARY KEY(site_id,robot_id)); CREATE TABLE IF NOT EXISTS robot_queue(position INTEGER PRIMARY KEY AUTOINCREMENT,robot_id TEXT NOT NULL,job_id TEXT UNIQUE NOT NULL,status TEXT NOT NULL,failure_mode TEXT); CREATE TABLE IF NOT EXISTS cell_safety_state(cell_id TEXT PRIMARY KEY,occupied INTEGER NOT NULL,event_id TEXT UNIQUE NOT NULL,updated_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS enrollments(site_id TEXT NOT NULL,robot_id TEXT NOT NULL,cell_id TEXT NOT NULL,stations TEXT NOT NULL,state TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(site_id,robot_id)); CREATE TABLE IF NOT EXISTS processed_message_ids(message_id TEXT PRIMARY KEY,processed_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS outbound_events(message_id TEXT PRIMARY KEY,payload TEXT NOT NULL,published_at TEXT);'''
class OnPremStore:
 def __init__(self,path=':memory:'):
  if path != ':memory:': Path(path).parent.mkdir(parents=True, exist_ok=True)
  self.db=sqlite3.connect(path, check_same_thread=False); self.db_lock=threading.RLock(); self.db.executescript(SCHEMA)
  try: self.db.execute('ALTER TABLE robot_queue ADD COLUMN failure_mode TEXT')
  except sqlite3.OperationalError: pass
  for statement in ("ALTER TABLE job_executions ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0", "ALTER TABLE robot_state ADD COLUMN state_reason TEXT", "ALTER TABLE robot_state ADD COLUMN last_seen TEXT"):
   try: self.db.execute(statement)
   except sqlite3.OperationalError: pass
  self.db.commit()
 def close(self): self.db.close()
 def __del__(self):
  try: self.db.close()
  except Exception: pass
 def record_command(self,message_id,job_id,now):
  try:self.db.execute('INSERT INTO received_commands VALUES(?,?,?)',(message_id,job_id,now));self.db.commit();return True
  except sqlite3.IntegrityError:return False
 def claim_execution(self,job_id,key):
  try:self.db.execute('INSERT INTO job_executions(job_id,execution_key,state) VALUES(?,?,?)',(job_id,key,'claimed'));self.db.commit();return True
  except sqlite3.IntegrityError:return False
 def add_outbound(self,message_id,payload):
  with self.db_lock: self.db.execute('INSERT OR IGNORE INTO outbound_events(message_id,payload) VALUES(?,?)',(message_id,payload)); self.db.commit()
 def pending_outbound(self):
  with self.db_lock: return self.db.execute('SELECT message_id,payload FROM outbound_events WHERE published_at IS NULL ORDER BY rowid').fetchall()
 def mark_outbound(self,message_id,when):
  with self.db_lock: self.db.execute('UPDATE outbound_events SET published_at=? WHERE message_id=?',(when,message_id)); self.db.commit()
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
