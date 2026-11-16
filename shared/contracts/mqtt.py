from __future__ import annotations
import json
from dataclasses import asdict
from .domain import Envelope

PREFIX='rrc/v1'
def topic(site,direction,kind,identifier=''):
    parts=[PREFIX,site,direction,kind]
    if identifier: parts.append(identifier)
    return '/'.join(parts)
def cloud_job_topic(site,job_id): return topic(site,'cloud','commands','jobs/'+job_id)
def cloud_safety_topic(site,cell_id): return topic(site,'cloud','commands','safety/'+cell_id)
def cloud_cancel_topic(site,job_id): return topic(site,'cloud','commands','cancel/'+job_id)
def cloud_enrollment_topic(site,robot_id=''): return topic(site,'cloud','commands','enrollment'+(('/'+robot_id) if robot_id else ''))
def onprem_enrollment_topic(site,robot_id=''): return topic(site,'onprem','events','enrollment'+(('/'+robot_id) if robot_id else ''))
def onprem_status_topic(site,job_id): return topic(site,'onprem','events','jobs/'+job_id)
def onprem_robot_topic(site,robot_id): return topic(site,'onprem','state','robots/'+robot_id)
def onprem_safety_topic(site,cell_id): return topic(site,'onprem','events','safety/'+cell_id)
def onprem_heartbeat_topic(site): return topic(site,'onprem','events','heartbeat')

def encode(envelope:Envelope)->bytes: return json.dumps(envelope.as_dict(),separators=(',',':')).encode()
def decode(raw:bytes|str)->dict:
    try: value=json.loads(raw)
    except (TypeError,json.JSONDecodeError) as e: raise ValueError('malformed JSON message') from e
    required={'schema_version','message_id','event_type','source','site_id','occurred_at','payload'}
    if not isinstance(value,dict) or not required <= value.keys(): raise ValueError('invalid envelope fields')
    if value['schema_version'] != '1': raise ValueError('unsupported schema version')
    if not isinstance(value['payload'],dict): raise ValueError('payload must be an object')
    return value

class InMemoryBroker:
    def __init__(self): self.subscribers={}; self.published=[]
    def subscribe(self,pattern,callback): self.subscribers.setdefault(pattern,[]).append(callback)
    def publish(self,topic_name,payload,qos=1):
        self.published.append((topic_name,payload,qos))
        for pattern,callbacks in self.subscribers.items():
            if self.matches(pattern,topic_name):
                for callback in callbacks: callback(topic_name,payload)
    @staticmethod
    def matches(pattern,value):
        p,v=pattern.split('/'),value.split('/')
        return len(p)==len(v) and all(a in ('+','#') or a==b for a,b in zip(p,v))

class EnrollmentCoordinator:
    def __init__(self,store,site_id='site-1'): self.store,self.site_id=store,site_id; self.unknown=[]
    def receive_request(self,topic_name,raw,now):
        msg=decode(raw); p=msg['payload']; robot=p.get('robot_id'); cell=p.get('cell_id'); stations=p.get('stations',[])
        if msg['event_type']!='enrollment.request' or msg['site_id']!=self.site_id: raise ValueError('invalid enrollment request')
        approved=robot in ('robot-1','robot-2') and cell in ('cell-1','cell-2') and bool(stations)
        if approved: self.store.enroll(self.site_id,robot,cell,','.join(sorted(stations)),now)
        return approved,robot
