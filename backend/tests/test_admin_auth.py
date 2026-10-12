from fastapi.testclient import TestClient
from retrovault.main import app
from retrovault import admin_auth
from retrovault.db import connect

def test_auth_isolation_expiry_logout_and_origin(database,monkeypatch):
    monkeypatch.setenv('ADMIN_USERNAME','owner')
    monkeypatch.setenv('ADMIN_PASSWORD_HASH',admin_auth.password_hash('test-password'))
    with TestClient(app) as api:
        api.post('/api/session',json={})
        visitor=api.cookies.get('retrovault_session')
        assert api.get('/api/admin/session').status_code==401
        assert api.post('/api/admin/login',json={'username':'owner','password':'wrong'}).status_code==401
        r=api.post('/api/admin/login',json={'username':'owner','password':'test-password'})
        assert r.status_code==200 and 'HttpOnly' in r.headers['set-cookie']
        assert api.cookies.get('retrovault_session')==visitor
        assert api.get('/api/admin/session').status_code==200
        assert api.post('/api/admin/logout',json={},headers={'Origin':'https://evil.example'}).status_code==403
        with connect() as db: db.execute("UPDATE admin_sessions SET expires_at=now()-interval '1 second'")
        assert api.get('/api/admin/session').status_code==401
        assert api.post('/api/admin/login',json={'username':'owner','password':'test-password'}).status_code==200
        assert api.post('/api/admin/logout',json={}).status_code==200
        assert api.get('/api/admin/session').status_code==401
        assert api.get('/api/state').status_code==200

def test_login_limit_commits_failures(database):
    with TestClient(app) as api:
        for _ in range(5): assert api.post('/api/admin/login',json={'username':'owner','password':'wrong'}).status_code==401
        assert api.post('/api/admin/login',json={'username':'other','password':'wrong'}).status_code==429

def test_all_admin_routes_reject_visitors(database):
    with TestClient(app) as api:
        api.post('/api/session',json={})
        for path in ('dashboard','conversations','conversations/missing','orders/missing','catalog/search'):
            assert api.get('/api/admin/'+path).status_code==401
        for path,body in (('catalog/add',{'game_id':7812,'platform':'psp'}),('catalog/review',{}),('catalog/1/status',{'active':False})):
            assert api.post('/api/admin/'+path,json=body).status_code==401
