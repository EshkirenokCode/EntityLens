import json,time
from concord import store

def test_lease_recovery_and_idempotent_publication(tmp_path,monkeypatch):
 monkeypatch.setattr(store,'DB',str(tmp_path/'worker.db'));store.init()
 from concord.worker import tick
 with store.connect() as c:
  c.execute("INSERT INTO jobs(id,status,created,lease,attempts) VALUES('recovered','running',?,?,1)",(time.time(),time.time()-1))
 assert tick()
 with store.connect() as c:
  j=c.execute('SELECT * FROM jobs').fetchone();assert j['status']=='completed';assert j['attempts']==2
 assert tick() is False
