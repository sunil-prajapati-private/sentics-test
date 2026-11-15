import unittest
from shared.contracts import *
from onprem.app.persistence import OnPremStore
class Phase3Tests(unittest.TestCase):
 def test_topics(self): self.assertEqual(cloud_job_topic('site-1','j'),'rrc/v1/site-1/cloud/commands/jobs/j'); self.assertEqual(onprem_status_topic('site-1','j'),'rrc/v1/site-1/onprem/events/jobs/j')
 def test_envelope_validation(self):
  e=Envelope('1','m','enrollment.request','onprem','site-1','2026-01-01T00:00:00Z',{'robot_id':'robot-1','cell_id':'cell-1','stations':['A']})
  self.assertEqual(decode(encode(e))['message_id'],'m')
  with self.assertRaises(ValueError): decode(b'{"schema_version":"9"}')
 def test_broker_reconnect_safe_duplicate_delivery(self):
  b=InMemoryBroker(); seen=[]; b.subscribe('rrc/v1/site-1/+/events/#',lambda t,p: seen.append(p)); b.publish(onprem_heartbeat_topic('site-1'),b'{}'); b.publish(onprem_heartbeat_topic('site-1'),b'{}'); self.assertEqual(len(seen),2)
 def test_enrollment_approval_and_rejection(self):
  s=OnPremStore(); c=EnrollmentCoordinator(s)
  good=Envelope('1','m1','enrollment.request','onprem','site-1','now',{'robot_id':'robot-1','cell_id':'cell-1','stations':['A','B','C']})
  self.assertEqual(c.receive_request(onprem_enrollment_topic('site-1'),encode(good),'now'),(True,'robot-1'))
  bad=Envelope('1','m2','enrollment.request','onprem','site-1','now',{'robot_id':'robot-x','cell_id':'cell-9','stations':[]})
  self.assertEqual(c.receive_request(onprem_enrollment_topic('site-1'),encode(bad),'now'),(False,'robot-x'))
if __name__=='__main__': unittest.main()
