import unittest
from cloud.app.service import create_job_data,ingest_status_data,store
from shared.contracts import Envelope,encode
class Phase4Tests(unittest.TestCase):
 def test_job_is_pending_and_outboxed(self):
  r,_=create_job_data('robot-1','A','B'); self.assertEqual(r['status'],'pending'); self.assertGreaterEqual(store.db.execute('select count(*) from outbox_messages').fetchone()[0],1)
 def test_invalid_route_rejected(self):
  with self.assertRaises(Exception): create_job_data('robot-1','A','E')
 def test_onprem_status_updates_once(self):
  r,_=create_job_data('robot-2','C','D'); e=Envelope('1','status-'+r['job_id'],'job.status','onprem','site-1','now',{'state':'received'},robot_id='robot-2',job_id=r['job_id']); self.assertTrue(ingest_status_data(encode(e))); self.assertFalse(ingest_status_data(encode(e)))
if __name__=='__main__':unittest.main()
