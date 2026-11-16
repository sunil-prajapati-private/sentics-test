import asyncio
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from .service import store, create_job_data, ingest_status_data

app=FastAPI(title='Remote Robot Cell Cloud API',version='0.2.0'); subscribers=[]
class JobRequest(BaseModel):
 robot_id:str; source_station:str; destination_station:str; failure_mode:str|None=None

def publish_update(job):
 for q in list(subscribers):
  try:q.put_nowait(job)
  except asyncio.QueueFull: pass
@app.get('/healthz')
def healthz(): return {'status':'ok','service':'cloud'}
@app.get('/api/robots')
def robots(): return store.list_robots()
@app.get('/api/jobs')
def jobs(): return store.list_jobs()
@app.get('/api/jobs/{job_id}')
def job(job_id:str):
 result=store.get_job(job_id)
 if not result: raise HTTPException(404,'job not found')
 return result
@app.post('/api/jobs',status_code=202)
def create_job(request:JobRequest):
 try: result,_=create_job_data(request.robot_id,request.source_station,request.destination_station,request.failure_mode)
 except (KeyError,ValueError) as exc: raise HTTPException(422,str(exc))
 publish_update(result); return result

def ingest_status(raw):
 changed=ingest_status_data(raw)
 if changed: publish_update(store.get_job(__import__('shared.contracts',fromlist=['decode']).decode(raw).get('job_id')))
 return changed

@app.get('/api/events')
async def events():
 q=asyncio.Queue(maxsize=100); subscribers.append(q)
 async def stream():
  try:
   for item in store.list_jobs(): yield f'data: {json.dumps(item)}\n\n'
   while True: yield f'data: {json.dumps(await q.get())}\n\n'
  finally: subscribers.remove(q)
 return StreamingResponse(stream(),media_type='text/event-stream')
