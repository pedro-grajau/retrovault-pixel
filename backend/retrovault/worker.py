"""Separate process; database locks and durable slot ids make restarts safe."""
import logging
import time
from . import config, commerce
from .db import connect
from .catalog import import_catalog, IntegrationError
from .simulation import advance

log = logging.getLogger('retrovault.worker')

def tick(now=None, importer=import_catalog):
    epoch = now if now is not None else time.time()
    result = {'simulation_interval_seconds': config.SIMULATION_INTERVAL, 'sessions': 0}
    with connect() as lock:
        if not lock.execute('SELECT pg_try_advisory_lock(172905) AS locked').fetchone()['locked']:
            return {**result, 'status': 'busy'}
        with connect() as db:
            sessions = db.execute("SELECT id FROM sessions WHERE last_seen > now() - (%s * interval '1 second')", (config.SESSION_TTL,)).fetchall()
        for session in sessions:
            try:
                with connect() as db:
                    advance(db, session['id'], f'scheduled:{int(epoch)//config.SIMULATION_INTERVAL}')
                result['sessions'] += 1
            except commerce.DomainError:
                continue
        with connect() as db:
            db.execute("DELETE FROM sessions WHERE last_seen < now() - (%s * interval '1 second')", (config.SESSION_TTL,))
        try:
            result['import'] = importer(run_id=f'scheduled:{int(epoch)//config.IMPORT_INTERVAL}')
        except IntegrationError as e:
            result['import'] = {'status': 'failed', 'message': str(e)}
        return result

def run():
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            log.info('Worker tick: %s', tick())
        except Exception:
            # Avoid leaking request URLs, tokens or DSN through generic tracebacks.
            log.error('Worker tick failed; retrying next poll.')
        time.sleep(30)
