import os
import sys
from pathlib import Path
from uuid import uuid4
import psycopg
from psycopg import sql
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from retrovault import config
from retrovault.db import migrate

@pytest.fixture
def database(monkeypatch):
    base = config.DATABASE_URL
    schema = 'test_' + uuid4().hex
    with psycopg.connect(base) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    monkeypatch.setattr(config, 'DATABASE_URL', psycopg.conninfo.make_conninfo(base, options=f'-c search_path={schema}'))
    migrate()
    try:
        yield schema
    finally:
        with psycopg.connect(base) as conn:
            conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))

@pytest.fixture
def stocked(database):
    from retrovault.db import connect
    from retrovault.commerce import create_session
    with connect() as c:
        c.execute("INSERT INTO platforms VALUES ('snes',19,'SNES')")
        c.execute("INSERT INTO games(id,title) VALUES (1,'Test Quest'),(2,'Test Racer')")
        c.execute("INSERT INTO offers(game_id,platform,sale_price,rental_price) VALUES (1,'snes',9990,1490),(2,'snes',9990,1490)")
        a, _ = create_session(c)
        b, _ = create_session(c)
    return a, b
