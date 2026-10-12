"""Maintenance only: demand and catalog changes require explicit actions."""
import logging
import time
from . import config
from .db import connect

log = logging.getLogger('retrovault.worker')

def tick(now=None):
    with connect() as db:
        if not db.execute('SELECT pg_try_advisory_xact_lock(172905) AS locked').fetchone()['locked']:
            return {'status': 'busy', 'cleaned': 0}
        expired=db.execute("SELECT id FROM sessions WHERE cleaned_at IS NULL AND (expired_at IS NOT NULL OR last_seen < now() - (%s * interval '1 second')) FOR UPDATE",(config.SESSION_TTL,)).fetchall()
        for row in expired:
            sid=row['id']
            db.execute('DELETE FROM carts WHERE session_id=%s',(sid,))
            db.execute('DELETE FROM checkouts WHERE session_id=%s AND NOT consumed AND NOT EXISTS (SELECT 1 FROM orders WHERE checkout_id=checkouts.id)',(sid,))
            db.execute('DELETE FROM sale_stock WHERE session_id=%s',(sid,))
            db.execute('DELETE FROM rental_copies WHERE session_id=%s AND NOT EXISTS (SELECT 1 FROM rentals WHERE copy_id=rental_copies.id)',(sid,))
            db.execute('UPDATE sessions SET expired_at=COALESCE(expired_at,now()),cleaned_at=now(),chat_busy_until=NULL,chat_lease=NULL WHERE id=%s',(sid,))
        db.execute('DELETE FROM admin_sessions WHERE expires_at<now()')
        db.execute("DELETE FROM admin_attempts WHERE window_at<now()-interval '1 hour'")
        return {'status':'complete','cleaned':len(expired)}

def run():
    logging.basicConfig(level=logging.INFO)
    while True:
        try: log.info('Maintenance: %s',tick())
        except Exception: log.error('Maintenance failed; retrying next poll.')
        time.sleep(30)
