from fastapi.testclient import TestClient
from retrovault import admin_auth,catalog,pixel
from retrovault.main import app
from retrovault.db import connect
from retrovault.worker import tick
from test_admin_catalog import API
from test_pixel_api import Provider,function

def test_complete_admin_journey_survives_expiry(database,monkeypatch):
    monkeypatch.setenv('ADMIN_USERNAME','owner')
    monkeypatch.setenv('ADMIN_PASSWORD_HASH',admin_auth.password_hash('test-password'))
    monkeypatch.setenv('OPENAI_API_KEY','test')
    monkeypatch.setenv('PIXEL_OPENAI_MODEL_SNAPSHOT','test')
    monkeypatch.setattr(catalog,'IGDB',API)
    monkeypatch.setattr(API,'close',lambda self:None,raising=False)
    with TestClient(app) as api:
        assert api.post('/api/admin/login',json={'username':'owner','password':'test-password'}).status_code==200
        api.post('/api/session',json={})
        sid=api.cookies.get('retrovault_session')
        found=api.get('/api/admin/catalog/search?q=Patapon&platform=psp').json()
        assert found['results'][0]['release_kind']=='native'
        add=api.post('/api/admin/catalog/add',json={'game_id':7812,'platform':'psp'}).json()
        oid=add['offer_id']
        pixel.chat(sid,'Recomende PSP',Provider([[function('record_recommendations',{'offer_ids':[oid]})],'Recomendo Patapon.']))
        assert api.put('/api/cart',json={'offer_id':oid,'mode':'rental','quantity':1}).status_code==200
        checkout=api.post('/api/checkout',json={}).json()['checkout_id']
        order=api.post('/api/confirm',json={'checkout_id':checkout,'confirmed':True}).json()['order_id']
        assert api.get('/api/admin/dashboard').json()['stats']['total_revenue']==1490
        conversations=api.get('/api/admin/conversations').json()
        assert conversations['stats']['ordered']==1
        cid=conversations['rows'][0]['id']
        assert api.get('/api/admin/orders/'+order).json()['origin']=='interface'
        with connect() as db:db.execute("UPDATE sessions SET last_seen=now()-interval '2 days' WHERE id=%s",(sid,))
        tick()
        assert api.get('/api/state').status_code==401
        assert api.get('/api/admin/dashboard').json()['stats']['total_revenue']==1490
        assert len(api.get('/api/admin/conversations/'+cid).json()['events'])==4
