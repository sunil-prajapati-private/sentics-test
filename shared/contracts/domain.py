from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum

class JobStatus(StrEnum):
    PENDING='pending'; RECEIVED='received'; QUEUED='queued'; RUNNING='running'; PAUSED='paused'; DONE='done'; FAILED='failed'; REJECTED='rejected'

PUBLIC_TERMINAL={JobStatus.DONE, JobStatus.FAILED, JobStatus.REJECTED}
_ALLOWED={
 JobStatus.PENDING:{JobStatus.RECEIVED,JobStatus.REJECTED}, JobStatus.RECEIVED:{JobStatus.QUEUED,JobStatus.REJECTED},
 JobStatus.QUEUED:{JobStatus.RUNNING,JobStatus.REJECTED}, JobStatus.RUNNING:{JobStatus.DONE,JobStatus.FAILED,JobStatus.PAUSED},
 JobStatus.PAUSED:{JobStatus.RUNNING,JobStatus.FAILED}, JobStatus.DONE:set(), JobStatus.FAILED:set(), JobStatus.REJECTED:set(),
}

def validate_transition(current: JobStatus, target: JobStatus) -> None:
    if target not in _ALLOWED[current]: raise ValueError(f'invalid job transition: {current} -> {target}')

CAPABILITIES={'robot-1':('cell-1',frozenset({'A','B','C'})),'robot-2':('cell-2',frozenset({'C','D','E'}))}

def validate_capability(robot_id:str, cell_id:str, source:str, destination:str)->None:
    try: expected, stations=CAPABILITIES[robot_id]
    except KeyError: raise ValueError(f'unknown robot: {robot_id}')
    if expected != cell_id: raise ValueError('robot does not belong to cell')
    if source not in stations or destination not in stations or source==destination: raise ValueError('unsupported station route')

@dataclass(frozen=True)
class Envelope:
    schema_version:str; message_id:str; event_type:str; source:str; site_id:str; occurred_at:str
    payload:dict; robot_id:str|None=None; cell_id:str|None=None; job_id:str|None=None; correlation_id:str|None=None
    def as_dict(self):
        d={'schema_version':self.schema_version,'message_id':self.message_id,'event_type':self.event_type,'source':self.source,'site_id':self.site_id,'occurred_at':self.occurred_at,'payload':self.payload}
        for k,v in (('robot_id',self.robot_id),('cell_id',self.cell_id),('job_id',self.job_id),('correlation_id',self.correlation_id)):
            if v is not None:d[k]=v
        return d
