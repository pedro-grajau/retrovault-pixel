from contextlib import contextmanager
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from . import config

@contextmanager
def connect():
    with psycopg.connect(config.DATABASE_URL, row_factory=dict_row) as conn:
        yield conn

def migrate():
    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(172903)')
        conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY)')
        for path in sorted((Path(__file__).parents[1] / 'migrations').glob('*.sql')):
            if not conn.execute('SELECT 1 FROM schema_migrations WHERE version=%s', (path.name,)).fetchone():
                conn.execute(path.read_text())
                conn.execute('INSERT INTO schema_migrations VALUES (%s)', (path.name,))
