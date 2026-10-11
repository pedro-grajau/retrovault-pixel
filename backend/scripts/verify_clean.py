"""Explicit clean-schema integration check; uses IGDB and removes only its own schema."""
from uuid import uuid4
import psycopg
from psycopg import sql
from retrovault import config, commerce
from retrovault.db import migrate, connect
from retrovault.catalog import import_catalog, catalog
from retrovault.worker import tick

def main():
    base=config.DATABASE_URL
    schema='qa_'+uuid4().hex
    with psycopg.connect(base) as db:
        db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    try:
        config.DATABASE_URL=psycopg.conninfo.make_conninfo(base,options=f'-c search_path={schema}')
        migrate()
        assert import_catalog(initial=True)['added']==30
        assert import_catalog(initial=True)['added']==0
        with connect() as db:
            rows=catalog(db)
            assert len(rows)==30 and len({r['platform'] for r in rows})==6
            sid,_=commerce.create_session(db)
        result=tick(now=3600)
        assert result['import']['added']==6
        assert tick(now=3601)['import']['status']=='already_processed'
        with connect() as db:
            assert len(catalog(db))==36
            assert len(db.execute('SELECT * FROM batches WHERE session_id=%s',(sid,)).fetchall())==1
        print('Schema vazio: migrações, IGDB real 30 + repetição 0 + expansão agendada 6, lote periódico idempotente: OK.')
    finally:
        config.DATABASE_URL=base
        with psycopg.connect(base) as db:
            db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))

if __name__=='__main__': main()
