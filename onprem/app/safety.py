from .execution import RobotScheduler, JobCommand, locked
from shared.contracts import CAPABILITIES, JobStatus

class SafetyController(RobotScheduler):
    """On-prem-only cell interlock layered over the serialized robot scheduler."""
    def __init__(self, store=None):
        super().__init__(store)
        self.occupied={row[0]: bool(row[1]) for row in self.store.db.execute('SELECT cell_id,occupied FROM cell_safety_state')}
        self.paused={}
    def _cell_for(self, robot_id): return CAPABILITIES[robot_id][0]
    def receive(self, cmd: JobCommand, now='now'):
        result=super().receive(cmd,now)
        # A queued command is accepted into durable storage but cannot start in an occupied cell.
        return result
    def run_next(self, robot_id, now='now'):
        cell=self._cell_for(robot_id)
        if self.occupied.get(cell,False):
            return None
        return super().run_next(robot_id,now)
    @locked
    def person_entered(self, cell_id, event_id, now='now'):
        if cell_id not in {v[0] for v in CAPABILITIES.values()}:
            raise ValueError('unknown cell')
        previous=self.occupied.get(cell_id,False)
        if previous:
            return None  # repeated occupancy is idempotent
        self.occupied[cell_id]=True
        self.store.db.execute('INSERT OR REPLACE INTO cell_safety_state(cell_id,occupied,event_id,updated_at) VALUES(?,?,?,?)',(cell_id,1,event_id,now)); self.store.db.commit()
        robot=next(r for r,(cell,_) in CAPABILITIES.items() if cell==cell_id)
        job_id=self.active.get(robot)
        if job_id:
            self.paused[robot]=job_id
            return self._event(job_id,JobStatus.PAUSED,'person_in_cell')
        return {'cell_id':cell_id,'state':'occupied','reason':'person_in_cell'}
    @locked
    def person_left(self, cell_id, event_id, now='now'):
        if cell_id not in {v[0] for v in CAPABILITIES.values()}: raise ValueError('unknown cell')
        if not self.occupied.get(cell_id,False): return None
        self.occupied[cell_id]=False
        self.store.db.execute('INSERT OR REPLACE INTO cell_safety_state(cell_id,occupied,event_id,updated_at) VALUES(?,?,?,?)',(cell_id,0,event_id,now)); self.store.db.commit()
        robot=next(r for r,(cell,_) in CAPABILITIES.items() if cell==cell_id)
        job_id=self.paused.pop(robot,None)
        if job_id: return self._event(job_id,JobStatus.RUNNING,'cell_clear')
        return {'cell_id':cell_id,'state':'clear'}
