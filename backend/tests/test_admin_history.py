from pathlib import Path
import pytest
from retrovault import commerce
from retrovault.db import connect, migrate
from retrovault.worker import tick

def test_additive_migration_preserves_legacy(stocked):
    sid, _ = stocked
    with connect() as db:
        commerce.set_cart(db,sid,1,'rental',1)
        oid=commerce.confirm(db,sid,commerce.summary(db,sid)['checkout_id'],True)['order_id']
        # Recreate the pre-migration shape in this disposable schema.
        db.execute('DROP TABLE journey_events,conversation_messages,conversations,admin_sessions,admin_attempts')
        db.execute('ALTER TABLE sessions DROP COLUMN expired_at, DROP COLUMN cleaned_at')
        db.execute('ALTER TABLE offers DROP COLUMN active, DROP COLUMN release_kind')
        db.execute('ALTER TABLE orders DROP COLUMN origin')
        db.execute('DROP INDEX orders_created')
        db.execute("UPDATE sessions SET messages='[{\"role\":\"user\",\"content\":\"Olá\"}]' WHERE id=%s",(sid,))
        db.execute("DELETE FROM schema_migrations WHERE version='003_admin_history.sql'")
    migrate()
    with connect() as db:
        assert db.execute('SELECT total,origin FROM orders WHERE id=%s',(oid,)).fetchone()=={'total':1490,'origin':'legacy'}
        assert db.execute('SELECT count(*) n FROM rentals WHERE order_id=%s',(oid,)).fetchone()['n']==1
        assert db.execute('SELECT partial FROM conversations WHERE session_id=%s',(sid,)).fetchone()['partial']
        m=db.execute('SELECT * FROM conversation_messages').fetchone()
        assert m['content']=='Olá' and m['created_at'] is None and m['status']=='legacy'
        assert db.execute('SELECT count(*) n FROM journey_events').fetchone()['n']==0

def test_expiry_preserves_history_and_cleans_once(stocked):
    sid,_=stocked
    with connect() as db:
        commerce.set_cart(db,sid,1,'rental',1)
        order=commerce.confirm(db,sid,commerce.summary(db,sid)['checkout_id'],True)
        db.execute("UPDATE sessions SET last_seen=now()-interval '2 days' WHERE id=%s",(sid,))
    assert tick()['cleaned']==1
    assert tick()['cleaned']==0
    with connect() as db:
        assert db.execute('SELECT 1 FROM orders WHERE id=%s',(order['order_id'],)).fetchone()
        assert db.execute('SELECT 1 FROM rentals WHERE order_id=%s',(order['order_id'],)).fetchone()
        assert not db.execute('SELECT 1 FROM sale_stock WHERE session_id=%s',(sid,)).fetchone()
        with pytest.raises(commerce.DomainError): commerce.require_session(db,sid)
