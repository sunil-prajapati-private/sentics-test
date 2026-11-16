import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from shared.contracts import JobStatus, validate_transition

SCHEMA='''CREATE TABLE IF NOT EXISTS jobs(job_id TEXT PRIMARY KEY,site_id TEXT NOT NULL,robot_id TEXT NOT NULL,source_station TEXT NOT NULL,destination_station TEXT NOT NULL,current_status TEXT NOT NULL,status_reason TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,execution_count INTEGER NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS job_status_history(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT NOT NULL,status TEXT NOT NULL,reason TEXT,occurred_at TEXT NOT NULL,message_id TEXT UNIQUE NOT NULL); CREATE TABLE IF NOT EXISTS outbox_messages(message_id TEXT PRIMARY KEY,aggregate_id TEXT NOT NULL,payload TEXT NOT NULL,published_at TEXT); CREATE TABLE IF NOT EXISTS robots(site_id TEXT NOT NULL,robot_id TEXT NOT NULL,cell_id TEXT NOT NULL,stations TEXT NOT NULL,enrollment_state TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'offline',state_reason TEXT,last_seen TEXT,PRIMARY KEY(site_id,robot_id)); CREATE TABLE IF NOT EXISTS enrollments(site_id TEXT NOT NULL,robot_id TEXT NOT NULL,request_id TEXT NOT NULL,decision TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(site_id,robot_id)); CREATE TABLE IF NOT EXISTS processed_message_ids(message_id TEXT PRIMARY KEY,processed_at TEXT NOT NULL);'''
class CloudStore:
 def __init__(self,path=':memory:'):
  if path != ':memory:': Path(path).parent.mkdir(parents=True, exist_ok=True)
  self.db=sqlite3.connect(path, check_same_thread=False); self.db.executescript(SCHEMA); self.db.commit()
  for statement in ("ALTER TABLE robots ADD COLUMN state TEXT NOT NULL DEFAULT 'offline'", "ALTER TABLE robots ADD COLUMN state_reason TEXT", "ALTER TABLE robots ADD COLUMN last_seen TEXT"):
   try: self.db.execute(statement)
   except sqlite3.OperationalError: pass
  self.db.commit()
 def close(self): self.db.close()
 def __del__(self):
  try: self.db.close()
  except Exception: pass
 def create_job(self,job_id,site,robot,source,dest,now):
  self.db.execute('INSERT INTO jobs(job_id,site_id,robot_id,source_station,destination_station,current_status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',(job_id,site,robot,source,dest,JobStatus.PENDING,now,now)); self.db.commit()
 def transition(self,job_id,target,reason,now,message_id):
  row=self.db.execute('SELECT current_status FROM jobs WHERE job_id=?',(job_id,)).fetchone();
  if self.db.execute('SELECT 1 FROM job_status_history WHERE message_id=?',(message_id,)).fetchone(): return False
  if not row: raise ValueError('unknown job')
  validate_transition(JobStatus(row[0]),JobStatus(target))
  try:
   with self.db:
    self.db.execute('INSERT INTO job_status_history(job_id,status,reason,occurred_at,message_id) VALUES(?,?,?,?,?)',(job_id,target,reason,now,message_id)); self.db.execute('UPDATE jobs SET current_status=?,status_reason=?,updated_at=? WHERE job_id=?',(target,reason,now,job_id))
  except sqlite3.IntegrityError: return False
  return True

 def add_outbox(self,message_id,job_id,payload):
  self.db.execute('INSERT INTO outbox_messages(message_id,aggregate_id,payload) VALUES(?,?,?)',(message_id,job_id,payload)); self.db.commit()
 def pending_outbox(self): return self.db.execute('SELECT message_id,aggregate_id,payload FROM outbox_messages WHERE published_at IS NULL ORDER BY rowid').fetchall()
 def mark_published(self,message_id,when): self.db.execute('UPDATE outbox_messages SET published_at=? WHERE message_id=?',(when,message_id)); self.db.commit()
 def remove_outbox_for_job(self,job_id): self.db.execute('DELETE FROM outbox_messages WHERE aggregate_id=?',(job_id,)); self.db.commit()
 def upsert_robot(self,site,robot,cell,stations,state='approved'):
  self.db.execute("INSERT INTO robots(site_id,robot_id,cell_id,stations,enrollment_state,state,last_seen) VALUES(?,?,?,?,?,'idle',CURRENT_TIMESTAMP) ON CONFLICT(site_id,robot_id) DO UPDATE SET cell_id=excluded.cell_id,stations=excluded.stations,enrollment_state=excluded.enrollment_state,last_seen=CURRENT_TIMESTAMP",(site,robot,cell,stations,state)); self.db.commit()
 def update_robot_state(self,site,robot,state,reason,seen):
  self.db.execute('UPDATE robots SET state=?,state_reason=?,last_seen=? WHERE site_id=? AND robot_id=?',(state,reason,seen,site,robot)); self.db.commit()
 def touch_robot(self,site,robot,seen):
  self.db.execute("UPDATE robots SET last_seen=? WHERE site_id=? AND robot_id=?",(seen,site,robot)); self.db.commit()
 def get_job(self,job_id):
  row=self.db.execute('SELECT job_id,site_id,robot_id,source_station,destination_station,current_status,status_reason,created_at,updated_at FROM jobs WHERE job_id=?',(job_id,)).fetchone()
  return dict(zip(('job_id','site_id','robot_id','source_station','destination_station','status','reason','created_at','updated_at'),row)) if row else None
 def list_jobs(self): return [self.get_job(r[0]) for r in self.db.execute('SELECT job_id FROM jobs ORDER BY created_at DESC')]
 def list_robots(self):
  result=[]
  for row in self.db.execute('SELECT site_id,robot_id,cell_id,stations,enrollment_state,state,state_reason,last_seen FROM robots'):
   item=dict(zip(('site_id','robot_id','cell_id','stations','enrollment_state','state','state_reason','last_seen'),row))
   try: item['online']=(datetime.now(timezone.utc)-datetime.fromisoformat(item['last_seen']).astimezone(timezone.utc)).total_seconds() < 30
   except (TypeError,ValueError): item['online']=False
   result.append(item)
  return result
