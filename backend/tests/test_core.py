from concurrent.futures import ThreadPoolExecutor
import httpx
import psycopg
import pytest
from retrovault.db import connect, migrate
from retrovault import commerce as c
from retrovault.catalog import IGDB, IntegrationError

def test_migrations_idempotent_and_unique(database):
    migrate()
    with connect() as db:
        assert db.execute('SELECT count(*) AS n FROM schema_migrations').fetchone()['n'] == 3
        db.execute("INSERT INTO platforms VALUES ('snes',19,'SNES')")
        db.execute("INSERT INTO games(id,title) VALUES (1,'Quest')")
        db.execute("INSERT INTO offers(game_id,platform,sale_price,rental_price) VALUES (1,'snes',100,10)")
    with pytest.raises(psycopg.errors.UniqueViolation):
        with connect() as db:
            db.execute("INSERT INTO offers(game_id,platform,sale_price,rental_price) VALUES (1,'snes',100,10)")

def test_igdb_failed_auth_sanitized(monkeypatch):
    monkeypatch.setenv('CLIENT_ID_IGDB_KEY', 'private-client')
    monkeypatch.setenv('CLIENT_SECRET_IGDB', 'private-secret')
    api = IGDB(httpx.MockTransport(lambda req: httpx.Response(401, json={'message':'private-secret'})))
    with pytest.raises(IntegrationError) as error:
        api.authenticate()
    assert 'private' not in str(error.value)
    api.close()

def test_sale_and_rental_isolation_and_returns(stocked):
    a,b = stocked
    with connect() as db:
        c.set_cart(db,a,1,'sale',1)
        c.set_cart(db,a,1,'rental',1)
        checkout=c.summary(db,a)
        order=c.confirm(db,a,checkout['checkout_id'],True)
        assert c.confirm(db,a,checkout['checkout_id'],True)['already_processed']
        assert db.execute('SELECT quantity FROM sale_stock WHERE session_id=%s AND offer_id=1',(a,)).fetchone()['quantity']==2
        assert db.execute('SELECT quantity FROM sale_stock WHERE session_id=%s AND offer_id=1',(b,)).fetchone()['quantity']==3
        rental=c.orders(db,a)[0]['rentals'][0]
        with pytest.raises(c.DomainError): c.return_rental(db,b,rental['id'])
        c.return_rental(db,a,rental['id'])
        assert c.return_rental(db,a,rental['id'])['already_processed']
        assert db.execute('SELECT count(*) AS n FROM rental_copies WHERE session_id=%s AND available',(a,)).fetchone()['n']==4

def test_checkout_confirmation_staleness_payment(stocked):
    a,b=stocked
    with connect() as db:
        c.set_cart(db,a,1,'sale',1)
        checkout=c.summary(db,a)
        with pytest.raises(c.DomainError): c.confirm(db,a,checkout['checkout_id'],False)
        with pytest.raises(c.DomainError): c.confirm(db,b,checkout['checkout_id'],True)
        with pytest.raises(c.DomainError): c.confirm(db,a,checkout['checkout_id'],True,False)
        assert not c.orders(db,a)
        c.set_cart(db,a,2,'rental',1)
        with pytest.raises(c.DomainError): c.confirm(db,a,checkout['checkout_id'],True)

def test_final_unit_and_atomic_mixed_order(stocked):
    a,_=stocked
    with connect() as db:
        db.execute('UPDATE sale_stock SET quantity=1 WHERE session_id=%s AND offer_id=1',(a,))
        c.set_cart(db,a,1,'sale',1)
        summaries=[c.summary(db,a)['checkout_id'] for _ in range(2)]
    def buy(cid):
        try:
            with connect() as db: return c.confirm(db,a,cid,True)
        except c.DomainError: return None
    with ThreadPoolExecutor(2) as pool: results=list(pool.map(buy,summaries))
    assert sum(r is not None for r in results)==1
    with connect() as db:
        assert len(c.orders(db,a))==1
        c.set_cart(db,a,1,'sale',1)
        c.set_cart(db,a,2,'rental',1)
        with pytest.raises(c.DomainError): c.summary(db,a)
        assert db.execute('SELECT count(*) AS n FROM rental_copies WHERE session_id=%s AND offer_id=2 AND available',(a,)).fetchone()['n']==2
