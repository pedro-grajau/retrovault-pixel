from types import SimpleNamespace as NS
from concurrent.futures import ThreadPoolExecutor
import json
import httpx
import pytest
from openai import APIConnectionError
from fastapi.testclient import TestClient
from retrovault import pixel, commerce as c
from retrovault.db import connect
from retrovault.main import app
from retrovault.simulation import advance

def function(name, args):
    return NS(type='function_call', name=name, arguments=json.dumps(args), call_id=name)

class Provider:
    def __init__(self, steps):
        self.steps, self.inputs = list(steps), []
        self.responses = self
    def create(self, **kwargs):
        self.inputs.append(kwargs)
        step = self.steps.pop(0)
        if isinstance(step, Exception): raise step
        return NS(output=step if isinstance(step,list) else [], output_text=step if isinstance(step,str) else '')

def test_pixel_tools_cart_checkout_confirmation_and_context(stocked, monkeypatch):
    a,b=stocked
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    monkeypatch.setenv('PIXEL_OPENAI_MODEL_SNAPSHOT','test-model')
    provider=Provider([[function('search_catalog',{'query':'','platform':'snes','budget_cents':2000,'mode':'rental'})],
                       [function('set_cart',{'offer_id':1,'mode':'rental','quantity':1})],
                       [function('prepare_checkout',{})], 'Resumo: Test Quest, SNES, aluguel R$14,90 por 7 dias. Confirme o pedido.'])
    result=pixel.chat(a,'Quero alugar Test Quest para SNES e revisar.',provider)
    assert result['checkout']['total']==1490
    assert len(provider.inputs)==4
    assert all(x['store'] is False and x['parallel_tool_calls'] is False for x in provider.inputs)
    with connect() as db:
        assert not c.orders(db,a)
        assert c.cart(db,b)['items']==[]
    pixel.chat(a,'Confirmo o pedido')
    pixel.chat(a,'Confirmo o pedido')
    with connect() as db: assert len(c.orders(db,a))==1
    provider=Provider(['Seu pedido está registrado.'])
    pixel.chat(a,'Qual foi meu console?',provider)
    assert any('SNES' in m['content'] for m in provider.inputs[0]['input'] if isinstance(m,dict))
    with pytest.raises(c.DomainError): pixel.execute_tool(a,'confirm_order',{})
    assert not any(t['name']=='confirm_order' for t in pixel.TOOLS)

def test_pixel_provider_failure_limits_and_ownership(stocked, monkeypatch):
    a,b=stocked
    monkeypatch.setenv('OPENAI_API_KEY','test-only')
    monkeypatch.setenv('PIXEL_OPENAI_MODEL_SNAPSHOT','test-model')
    broken=Provider([APIConnectionError(request=httpx.Request('POST','https://api.openai.com'))])
    with pytest.raises(c.DomainError, match='indisponível'): pixel.chat(a,'Olá',broken)
    with connect() as db:
        assert db.execute('SELECT chat_lease FROM sessions WHERE id=%s',(a,)).fetchone()['chat_lease'] is None
        c.set_cart(db,b,2,'sale',1)
    # Session identifiers supplied by a model cannot replace the server binding.
    assert pixel.execute_tool(a,'get_cart',{'session_id':b})['items']==[]
    pixel.execute_tool(a,'set_cart',{'offer_id':1,'mode':'sale','quantity':10})
    with pytest.raises(c.DomainError,match='insuficiente'): pixel.execute_tool(a,'prepare_checkout',{})
    with connect() as db:
        assert c.cart(db,b)['items'][0]['offer_id']==2
        db.execute('UPDATE sessions SET chat_count=30 WHERE id=%s',(a,))
    with pytest.raises(c.DomainError) as error: pixel.chat(a,'Olá',Provider([]))
    assert error.value.status==429
    with pytest.raises(c.DomainError): pixel.chat('nonexistent','Olá',Provider([]))

def test_http_contract_isolation_origin_and_fictitious_checkout(database):
    with connect() as db:
        db.execute("INSERT INTO platforms VALUES ('snes',19,'SNES')")
        db.execute("INSERT INTO games(id,title) VALUES (1,'Quest')")
        db.execute("INSERT INTO offers(game_id,platform,sale_price,rental_price) VALUES (1,'snes',9990,1490)")
    with TestClient(app) as a, TestClient(app) as b:
        assert a.get('/api/state').status_code==401
        started=a.post('/api/session',json={})
        assert started.status_code==200
        assert b.post('/api/session',json={}).status_code==200
        assert 'HttpOnly' in started.headers['set-cookie'] and 'SameSite=lax' in started.headers['set-cookie']
        assert a.put('/api/cart',json={'offer_id':1,'mode':'sale','quantity':1,'session_id':'fake'}).status_code==422
        assert a.post('/api/checkout',headers={'Origin':'https://untrusted.example'},json={}).status_code==403
        assert a.put('/api/cart',json={'offer_id':1,'mode':'rental','quantity':1}).status_code==200
        checkout=a.post('/api/checkout',json={}).json()['checkout_id']
        assert b.post('/api/confirm',json={'checkout_id':checkout,'confirmed':True}).status_code==404
        assert a.post('/api/confirm',json={'checkout_id':checkout,'confirmed':False}).status_code==422
        result=a.post('/api/confirm',json={'checkout_id':checkout,'confirmed':True})
        assert result.status_code==200 and result.json()['simulated']
        rental=a.get('/api/state').json()['orders'][0]['rentals'][0]['id']
        assert b.post(f'/api/rentals/{rental}/return',json={}).status_code==404
        assert a.post(f'/api/rentals/{rental}/return',json={}).status_code==200
        assert a.post(f'/api/rentals/{rental}/return',json={}).json()['already_processed']

def test_stock_change_invalidates_summary_and_simulation_checkout_concurrency(stocked):
    a,_=stocked
    with connect() as db:
        c.set_cart(db,a,1,'sale',1)
        checkout=c.summary(db,a)
        db.execute('UPDATE sale_stock SET quantity=2 WHERE session_id=%s AND offer_id=1',(a,))
        with pytest.raises(c.DomainError, match='mudaram'): c.confirm(db,a,checkout['checkout_id'],True)
        fresh=c.summary(db,a)
    def buy():
        try:
            with connect() as db: return c.confirm(db,a,fresh['checkout_id'],True)
        except c.DomainError: return None
    def simulate():
        with connect() as db: return advance(db,a,'parallel-slot')
    with ThreadPoolExecutor(2) as pool:
        jobs=[pool.submit(buy),pool.submit(simulate)]
        [j.result() for j in jobs]
    with connect() as db:
        assert db.execute('SELECT min(quantity) AS n FROM sale_stock WHERE session_id=%s',(a,)).fetchone()['n']>=0
        assert db.execute('SELECT count(*) AS n FROM rentals r JOIN rental_copies rc ON rc.id=r.copy_id WHERE rc.available AND r.returned_at IS NULL').fetchone()['n']==0
        assert len([o for o in c.orders(db,a) if o['actor']=='visitor'])<=1
