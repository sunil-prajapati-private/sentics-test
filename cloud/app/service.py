from datetime import datetime, timezone
import os
from uuid import uuid4
from shared.contracts import Envelope, CAPABILITIES, encode, validate_capability
from .persistence import CloudStore
SITE_ID=os.getenv('SITE_ID','site-1')
store=CloudStore(os.getenv('CLOUD_DB_PATH',':memory:'))
def now(): return datetime.now(timezone.utc).isoformat()
def create_job_data(robot_id,source_station,destination_station,failure_mode=None):
 validate_capability(robot_id,CAPABILITIES[robot_id][0],source_station,destination_station)
 job_id=str(uuid4()); message_id=str(uuid4()); stamp=now(); store.create_job(job_id,SITE_ID,robot_id,source_station,destination_station,stamp)
 payload={'robot_id':robot_id,'source_station':source_station,'destination_station':destination_station}
 if failure_mode: payload['failure_mode']=failure_mode
 envelope=Envelope('1',message_id,'job.command','cloud',SITE_ID,stamp,payload,robot_id=robot_id,job_id=job_id,correlation_id=job_id)
 store.add_outbox(message_id,job_id,encode(envelope).decode()); return store.get_job(job_id), envelope

def ingest_status_data(raw):
 from shared.contracts import decode
 msg=decode(raw); p=msg['payload']; job_id=msg.get('job_id')
 if msg['source']!='onprem' or msg['site_id']!=SITE_ID or not job_id: raise ValueError('unauthorized status')
 if not store.get_job(job_id): raise ValueError('unknown job')
 changed = store.transition(job_id,p['state'],p.get('reason'),msg['occurred_at'],msg['message_id'])
 if changed and p['state'] in {'done','failed','rejected','cancelled'}:
  store.remove_outbox_for_job(job_id)
 return changed
