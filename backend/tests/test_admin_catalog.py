import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from retrovault import catalog as cat,commerce as c
from retrovault.db import connect

REAL=json.loads((Path(__file__).parent/'fixtures/igdb_psp_releases.json').read_text())
class API:
    def query(self,endpoint,body):
        if endpoint=='platforms': return [{'id':38,'name':'PlayStation Portable'}]
        if 'where id=' in body:
            import re
            ids=re.search(r'where id=([^;]+)',body).group(1)
            return [g for g in REAL if str(g['id']) in ids]
        return REAL

def test_real_psp_classification_and_search_no_mutation(database):
    assert [cat.release_kind(g,38) for g in REAL]==['rerelease','native','rerelease','native']
    assert cat.release_kind({'game_type':{'type':'Main Game'}},38)=='uncertain'
    result=cat.search_titles('', 'psp',client=API())
    assert result['results'][0]['release_kind']=='native'
    with connect() as db: assert db.execute('SELECT count(*) n FROM offers').fetchone()['n']==0

def test_addition_revalidation_concurrency_preserved_stock_and_new_session(stocked):
    sid,other=stocked
    def add(): return cat.add_title(7812,'psp',client=API())
    with ThreadPoolExecutor(2) as pool: results=list(pool.map(lambda _:add(),range(2)))
    assert sum(r['added'] for r in results)==1
    oid=results[0]['offer_id']
    with connect() as db:
        assert cat.catalog(db,sid,platform='psp')[0]['sale_available']==3
        c.set_cart(db,sid,oid,'sale',1)
        c.confirm(db,sid,c.summary(db,sid)['checkout_id'],True)
    assert not add()['added']
    with connect() as db:
        assert cat.catalog(db,sid,platform='psp')[0]['sale_available']==2
        assert cat.catalog(db,other,platform='psp')[0]['rental_available']==2
        future,_=c.create_session(db)
        assert cat.catalog(db,future,platform='psp')[0]['sale_available']==3
        assert db.execute('SELECT count(*) n FROM orders').fetchone()['n']==1
    class Wrong(API):
        def query(self,e,b):
            rows=super().query(e,b)
            return [dict(g,platforms=[7]) for g in rows] if e=='games' else rows
    with pytest.raises(c.DomainError):cat.add_title(2407,'psp',client=Wrong())
    class Broken:
        def query(self,*args): raise cat.IntegrationError('Indisponível')
    with pytest.raises(cat.IntegrationError):cat.add_title(2407,'psp',client=Broken())

def test_deactivate_preserves_orders_and_returns(stocked):
    sid,_=stocked
    with connect() as db:
        c.set_cart(db,sid,1,'rental',1)
        c.confirm(db,sid,c.summary(db,sid)['checkout_id'],True)
        rental=c.orders(db,sid)[0]['rentals'][0]['id']
        c.set_cart(db,sid,1,'sale',1)
        checkout=c.summary(db,sid)['checkout_id']
        cat.set_offer_active(db,1,False)
        assert not cat.catalog(db,sid,query='Quest')
        with pytest.raises(c.DomainError):c.confirm(db,sid,checkout,True)
        with pytest.raises(c.DomainError):c.summary(db,sid)
        c.set_cart(db,sid,1,'sale',0)
        c.return_rental(db,sid,rental)
        assert c.orders(db,sid)[0]['rentals'][0]['returned_at']
