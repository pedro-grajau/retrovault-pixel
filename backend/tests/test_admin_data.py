from datetime import datetime,timezone
import pytest
from retrovault import commerce as c,journey,admin_data,pixel
from retrovault.db import connect
from test_pixel_api import Provider,function

def test_full_chat_failure_and_structured_recommendations(stocked,monkeypatch):
    sid,_=stocked
    monkeypatch.setenv('OPENAI_API_KEY','test')
    monkeypatch.setenv('PIXEL_OPENAI_MODEL_SNAPSHOT','test')
    monkeypatch.setenv('CHAT_LIMIT_PER_HOUR','100')
    for _ in range(10): pixel.chat(sid,'Olá',Provider(['Oi']))
    pixel.chat(sid,'Recomende',Provider([[function('record_recommendations',{'offer_ids':[1]})],'Recomendo Test Quest']))
    with pytest.raises(c.DomainError): pixel.chat(sid,'Falha',Provider(['']))
    with connect() as db:
        cid=journey.conversation(db,sid)['id']
        detail=admin_data.detail(db,cid)
        assert len(detail['messages'])==23
        assert detail['messages'][-1]['status']=='failed'
        assert len(detail['events'])==1 and detail['events'][0]['type']=='recommendation'
        assert len(db.execute('SELECT messages FROM sessions WHERE id=%s',(sid,)).fetchone()['messages'])==16


def test_mixed_journey_retries_failed_checkout_and_simulation(stocked):
    sid,_=stocked
    with connect() as db: mid=journey.receive(db,sid,'Quero um jogo')
    journey.run(sid,'pixel','recommendation',lambda db:journey.recommend(db,sid,[1]),mid)
    journey.run(sid,'pixel','recommendation',lambda db:journey.recommend(db,sid,[1]),mid)
    journey.run(sid,'interface','cart',lambda db:c.set_cart(db,sid,1,'sale',10))
    with pytest.raises(c.DomainError): journey.run(sid,'interface','checkout',lambda db:c.summary(db,sid))
    journey.run(sid,'interface','cart',lambda db:c.set_cart(db,sid,1,'sale',1))
    checkout=journey.run(sid,'interface','checkout',lambda db:c.summary(db,sid))
    for _ in range(2): journey.run(sid,'interface','order',lambda db:c.confirm(db,sid,checkout['checkout_id'],True))
    with connect() as db:
        rows=[{'offer_id':2,'title':'Test Racer','platform':'snes','mode':'sale','quantity':1,'unit_price':9990,'subtotal':9990}]
        c.place_order(db,sid,rows,actor='simulation')
        result=admin_data.conversations(db)
        assert result['stats']=={'conversations':1,'recommended':1,'cart':1,'ordered':1,'conversion_percent':100.0}
        events=admin_data.detail(db,journey.conversation(db,sid)['id'])['events']
        assert sum(e['type']=='order' for e in events)==1
        assert sum(e['type']=='recommendation' for e in events)==1
        assert any(e['status']=='failed' for e in events)


def test_commercial_totals_filters_returns_pagination_and_cohort(stocked):
    sid,_=stocked
    with connect() as db:
        mid=journey.receive(db,sid,'Olá')
        rows=[{'offer_id':1,'title':'Test Quest','platform':'snes','mode':'sale','quantity':2,'unit_price':9990,'subtotal':19980},
              {'offer_id':1,'title':'Test Quest','platform':'snes','mode':'rental','quantity':1,'unit_price':1490,'subtotal':1490}]
        c.place_order(db,sid,rows)
        r=db.execute('SELECT id FROM rentals').fetchone()['id']
        data=admin_data.commercial(db)
        assert data['stats']=={'units_sold':2,'sale_revenue':19980,'rental_revenue':1490,'total_revenue':21470}
        db.execute("UPDATE rentals SET due_at=now()-interval '1 day'")
        assert admin_data.commercial(db)['rentals'][0]['status']=='overdue'
        c.return_rental(db,sid,r)
        assert admin_data.commercial(db)['stats']==data['stats']
        assert admin_data.commercial(db)['rentals'][0]['status']=='returned'
        assert admin_data.commercial(db,actor='simulation')['stats']['total_revenue']==0
        assert admin_data.commercial(db,platform='psp')['stats']['total_revenue']==0
        # More than the public API limit; frozen values must not follow current prices.
        from psycopg.types.json import Jsonb
        for i in range(105):
            db.execute("INSERT INTO orders(id,session_id,actor,origin,items,total,created_at) VALUES (%s,%s,'visitor','interface',%s,21470,'2026-10-12 03:00:00+00')",(f'bulk:{i}',sid,Jsonb(rows)))
        db.execute('UPDATE offers SET sale_price=1,rental_price=1')
        assert admin_data.commercial(db)['stats']['total_revenue']==106*21470
        assert len(admin_data.commercial(db,page=5)['orders'])==6
        assert admin_data.commercial(db,start='2026-10-11',end='2026-10-11')['order_count']==0
        assert admin_data.commercial(db,start='2026-10-12',end='2026-10-12')['order_count']>=105
        db.execute("UPDATE conversations SET started_at='2026-10-11 03:00:00+00'")
        assert admin_data.conversations(db,start='2026-10-11',end='2026-10-11')['stats']['ordered']==1
        assert admin_data.conversations(db,start='2026-10-12',end='2026-10-12')['stats']['conversations']==0
