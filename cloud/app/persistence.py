import sqlite3
from pathlib import Path
from shared.contracts import JobStatus, validate_transition

SCHEMA='''CREATE TABLE IF NOT EXISTS jobs(job_id TEXT PRIMARY KEY,site_id TEXT NOT NULL,robot_id TEXT NOT NULL,source_station TEXT NOT NULL,destination_station TEXT NOT NULL,current_status TEXT NOT NULL,status_reason TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,execution_count INTEGER NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS job_status_history(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT NOT NULL,status TEXT NOT NULL,reason TEXT,occurred_at TEXT NOT NULL,message_id TEXT UNIQUE NOT NULL); CREATE TABLE IF NOT EXISTS outbox_messages(message_id TEXT PRIMARY KEY,aggregate_id TEXT NOT NULL,payload TEXT NOT NULL,published_at TEXT); CREATE TABLE IF NOT EXISTS robots(site_id TEXT NOT NULL,robot_id TEXT NOT NULL,cell_id TEXT NOT NULL,stations TEXT NOT NULL,enrollment_state TEXT NOT NULL,PRIMARY KEY(site_id,robot_id)); CREATE TABLE IF NOT EXISTS enrollments(site_id TEXT NOT NULL,robot_id TEXT NOT NULL,request_id TEXT NOT NULL,decision TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(site_id,robot_id)); CREATE TABLE IF NOT EXISTS processed_message_ids(message_id TEXT PRIMARY KEY,processed_at TEXT NOT NULL);'''
class CloudStore:
 def __init__(self,path=':memory:'): self.db=sqlite3.connect(path); self.db.executescript(SCHEMA); self.db.commit()
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
 def get_job(self,job_id):
  row=self.db.execute('SELECT job_id,site_id,robot_id,source_station,destination_station,current_status,status_reason,created_at,updated_at FROM jobs WHERE job_id=?',(job_id,)).fetchone()
  return dict(zip(('job_id','site_id','robot_id','source_station','destination_station','status','reason','created_at','updated_at'),row)) if row else None
 def list_jobs(self): return [self.get_job(r[0]) for r in self.db.execute('SELECT job_id FROM jobs ORDER BY created_at DESC')]
 def list_robots(self): return [dict(zip(('site_id','robot_id','cell_id','stations','enrollment_state'),r)) for r in self.db.execute('SELECT site_id,robot_id,cell_id,stations,enrollment_state FROM robots')]
