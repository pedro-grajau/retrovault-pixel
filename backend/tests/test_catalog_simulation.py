from concurrent.futures import ThreadPoolExecutor
import pytest
from retrovault.db import connect
from retrovault.catalog import import_catalog, IntegrationError, catalog, save_game, valid_demo_url
from retrovault.simulation import advance
from retrovault.worker import tick
from retrovault import commerce, config

class FakeIGDB:
    def query(self, endpoint, body):
        if endpoint=='platforms':
            name=next(n for n in config.PLATFORMS.values() if f'"{n}"' in body)
            return [{'id': list(config.PLATFORMS.values()).index(name)+10,'name':name}]
        import re
        if 'where id=' in body: return []
        pid=int(re.search(r'platforms=\((\d+)\)',body).group(1))
        return [{'id':pid*100+i,'name':f'Game {pid}-{i}','genres':[{'name': 'Platform' if i%2 else 'Racing'}]} for i in range(10)]

def test_partial_import_failure_rolls_back(database):
    assert import_catalog(True,client=FakeIGDB())['added']==30
    class LateFailure(FakeIGDB):
        def __init__(self): self.platforms=0
        def query(self,endpoint,body):
            if endpoint=='platforms':
                self.platforms+=1
                if self.platforms==2: raise IntegrationError('IGDB temporariamente indisponível')
            return super().query(endpoint,body)
    with pytest.raises(IntegrationError): import_catalog(client=LateFailure(),run_id='failed-partial')
    with connect() as db:
        assert len(catalog(db))==30
        run=db.execute("SELECT status,added FROM import_runs WHERE id='failed-partial'").fetchone()
        assert run=={'status':'failed','added':0}

def test_import_repeat_missing_metadata_expansion_and_failure(database):
    assert import_catalog(True,client=FakeIGDB())['added']==30
    assert import_catalog(True,client=FakeIGDB())['added']==0
    assert import_catalog(client=FakeIGDB(),run_id='expand')['added']==6
    assert import_catalog(client=FakeIGDB(),run_id='expand')['status']=='already_processed'
    with connect() as db:
        assert len(catalog(db))==36
        assert all(g['cover'] is None for g in catalog(db))
        offer=catalog(db)[0]
        db.execute('UPDATE offers SET sale_price=12345 WHERE id=%s',(offer['id'],))
        save_game(db,{'id':offer['game_id'],'name':'Updated metadata','summary':None,'cover':None,'genres':None})
        assert db.execute('SELECT sale_price FROM offers WHERE id=%s',(offer['id'],)).fetchone()['sale_price']==12345
        assert db.execute('SELECT summary FROM games WHERE id=%s',(offer['game_id'],)).fetchone()['summary']==''
    class Failing:
        def query(self,*args): raise IntegrationError('Integration unavailable')
    with pytest.raises(IntegrationError): import_catalog(client=Failing())
    with connect() as db: assert len(catalog(db))==36

def test_demo_providers_budget_missing_titles(stocked):
    a,_=stocked
    assert valid_demo_url('https://www.retrogames.cc/snes-games/example.html')
    assert not valid_demo_url('https://www.retrogames.cc.untrusted.example/test')
    assert not valid_demo_url('http://www.retrogames.cc/test')
    assert not valid_demo_url('https://user@www.retrogames.cc/test')
    with connect() as db:
        assert catalog(db,a,query='Missing 999')==[]
        assert catalog(db,a,platform='psp')==[]
        assert catalog(db,a,budget_cents=100)==[]
        assert all(r['demo_url'] is None and r['rental_days']==7 for r in catalog(db,a))
        db.execute("INSERT INTO demo_links VALUES (1,'Untrusted','https://bad.example',NULL)")
        assert catalog(db,a)[0]['demo_url'] is None

def test_simulation_returns_only_simulated_rentals(stocked,monkeypatch):
    a,_=stocked
    with connect() as db:
        commerce.set_cart(db,a,1,'rental',1)
        visitor=commerce.confirm(db,a,commerce.summary(db,a)['checkout_id'],True)
        item={'offer_id':2,'title':'Test Racer','platform':'snes','platform_name':'SNES','mode':'rental','quantity':1,'unit_price':1490,'subtotal':1490,'rental_days':7}
        simulated=commerce.place_order(db,a,[item],actor='simulation')
    class Returns:
        def __init__(self,*args): pass
        def choice(self,values): return 'return'
    monkeypatch.setattr('retrovault.simulation.random.Random',Returns)
    with connect() as db:
        result=advance(db,a,'return-batch')
        assert result['events'][0]['status']=='complete'
        assert all(e['status']=='skipped' for e in result['events'][1:])
        orders=commerce.orders(db,a)
        assert next(o for o in orders if str(o['id'])==visitor['order_id'])['rentals'][0]['returned_at'] is None
        assert next(o for o in orders if str(o['id'])==simulated['order_id'])['rentals'][0]['returned_at'] is not None

def test_simulation_idempotency_isolation_empty_stock(stocked):
    a,b=stocked
    with connect() as db:
        db.execute('UPDATE sale_stock SET quantity=0 WHERE session_id=%s',(a,))
        db.execute('UPDATE rental_copies SET available=false WHERE session_id=%s',(a,))
    def run():
        with connect() as db: return advance(db,a,'batch')
    with ThreadPoolExecutor(2) as pool: runs=list(pool.map(lambda _:run(),range(2)))
    assert sum(x['already_processed'] for x in runs)==1
    assert all(e['status']=='skipped' for e in runs[0]['events'])
    with connect() as db:
        assert not commerce.orders(db,b)
        assert db.execute('SELECT min(quantity) AS n FROM sale_stock WHERE session_id=%s',(b,)).fetchone()['n']==3

def test_worker_slots_expiry_manual_concurrency(stocked):
    a,b=stocked
    fake=lambda **kw:{'status':'complete','added':0}
    assert config.SIMULATION_INTERVAL==1800
    assert tick(now=3600,importer=fake)['sessions']==2
    tick(now=3601,importer=fake)
    with connect() as db:
        assert db.execute('SELECT count(*) AS n FROM batches').fetchone()['n']==2
        advance(db,a,'manual',manual=True)
    with pytest.raises(commerce.DomainError):
        with connect() as db: advance(db,a,'manual2',manual=True)
    with connect() as db:
        db.execute("UPDATE sessions SET last_seen=now()-interval '2 days' WHERE id=%s",(b,))
    tick(now=5400,importer=fake)
    with connect() as db: assert not db.execute('SELECT 1 FROM sessions WHERE id=%s',(b,)).fetchone()
