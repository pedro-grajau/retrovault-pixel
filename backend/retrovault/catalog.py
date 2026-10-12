"""IGDB ingestion; no commerce data is taken from IGDB."""
import json
import os
import time
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlparse
import httpx
from psycopg.types.json import Jsonb
from . import config
from .db import connect

class IntegrationError(Exception):
    pass

def valid_demo_url(url):
    try:
        parsed = urlparse(url)
        return (parsed.scheme == 'https' and parsed.hostname in {'www.retrogames.cc', 'retrogames.cc'}
                and parsed.username is None and parsed.password is None and parsed.port in {None,443})
    except ValueError:
        return False

def load_demos(enable_embeds=False):
    mappings=json.loads((Path(__file__).parents[1]/'demo-links.json').read_text())
    attached=0
    with connect() as conn:
        for demo in mappings:
            if not valid_demo_url(demo['url']) or not valid_demo_url(demo['candidate_embed']):
                raise IntegrationError('Demonstração com provedor não aprovado.')
            offer=conn.execute('SELECT o.id FROM offers o JOIN games g ON g.id=o.game_id WHERE g.title=%s AND o.platform=%s',(demo['title'],demo['platform'])).fetchone()
            if not offer: continue
            conn.execute('INSERT INTO demo_links VALUES (%s,%s,%s,%s) ON CONFLICT(offer_id) DO UPDATE SET url=excluded.url,provider=excluded.provider,embed_url=excluded.embed_url',
                (offer['id'],demo['provider'],demo['url'],demo['candidate_embed'] if enable_embeds else None))
            attached+=1
    return {'attached':attached,'embeds_enabled':enable_embeds}

class IGDB:
    def __init__(self, transport=None):
        self.client = httpx.Client(timeout=25, transport=transport)
        self.token = None
        self.expires = 0
        self.next_request = 0

    def authenticate(self):
        client_id = os.getenv('CLIENT_ID_IGDB_KEY', '')
        secret = os.getenv('CLIENT_SECRET_IGDB', '')
        if not client_id or not secret:
            raise IntegrationError('Credenciais IGDB não configuradas.')
        try:
            r = self.client.post('https://id.twitch.tv/oauth2/token', data={
                'client_id': client_id, 'client_secret': secret, 'grant_type': 'client_credentials'})
            r.raise_for_status()
            payload = r.json()
            self.token = payload['access_token']
            self.expires = time.monotonic() + payload['expires_in'] - 60
        except (httpx.HTTPError, KeyError, ValueError):
            raise IntegrationError('Não foi possível autenticar no IGDB.') from None

    def query(self, endpoint, body):
        if not self.token or time.monotonic() >= self.expires:
            self.authenticate()
        for attempt in range(3):
            time.sleep(max(0, self.next_request - time.monotonic()))
            self.next_request = time.monotonic() + .30
            try:
                r = self.client.post(f'https://api.igdb.com/v4/{endpoint}', content=body,
                    headers={'Client-ID': os.getenv('CLIENT_ID_IGDB_KEY', ''), 'Authorization': f'Bearer {self.token}'})
                if r.status_code == 401 and attempt < 2:
                    self.authenticate()
                    continue
                if (r.status_code == 429 or r.status_code >= 500) and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                r.raise_for_status()
                return r.json()
            except (httpx.HTTPError, ValueError):
                if attempt == 2:
                    raise IntegrationError('Consulta IGDB indisponível; catálogo local preservado.') from None
                time.sleep(2 ** attempt)
        raise IntegrationError('Consulta IGDB indisponível.')

    def close(self):
        self.client.close()

def import_catalog(initial=False, run_id=None, client=None):
    run_id = run_id or f'manual:{uuid4()}'
    api = client or IGDB()
    added = 0
    try:
        with connect() as conn:
            # Session-level advisory lock persists across commits for the external calls.
            if not conn.execute('SELECT pg_try_advisory_lock(172904) AS locked').fetchone()['locked']:
                return {'status': 'busy', 'added': 0}
            if conn.execute('SELECT 1 FROM import_runs WHERE id=%s AND status=%s', (run_id, 'complete')).fetchone():
                return {'status': 'already_processed', 'added': 0}
            conn.execute("INSERT INTO import_runs(id,status) VALUES (%s,'running') ON CONFLICT(id) DO UPDATE SET status='running',error=NULL", (run_id,))
            conn.commit()
            amount = config.integer('CATALOG_INITIAL_PER_PLATFORM', 5) if initial else config.integer('CATALOG_EXPANSION_PER_PLATFORM', 1)
            for slug, name in config.PLATFORMS.items():
                platforms = api.query('platforms', f'fields id,name; where name = {json.dumps(name)}; limit 5;')
                if not platforms:
                    raise IntegrationError(f'Plataforma não encontrada no IGDB: {slug}.')
                pid = platforms[0]['id']
                conn.execute('INSERT INTO platforms VALUES (%s,%s,%s) ON CONFLICT(slug) DO UPDATE SET igdb_id=excluded.igdb_id', (slug, pid, config.LABELS[slug]))
                existing = {r['game_id'] for r in conn.execute('SELECT game_id FROM offers WHERE platform=%s', (slug,)).fetchall()}
                platform_amount = max(0, amount - len(existing)) if initial else amount
                # Refresh saved records separately; do not reset commerce values.
                if existing:
                    refresh = api.query('games', f'fields id,name,summary,cover.url,genres.name; where id=({",".join(map(str, sorted(existing))) }); limit 500;')
                    for game in refresh:
                        save_game(conn, game)
                selected, offset, genres_seen = [], 0, set()
                while len(selected) < platform_amount and offset < 500:
                    games = api.query('games', f'fields {GAME_FIELDS}; where platforms=({pid}) & version_parent=null; sort total_rating_count desc; limit 100; offset {offset};')
                    if not games:
                        break
                    candidates = [g for g in games if g['id'] not in existing]
                    if slug=='psp':
                        candidates=[g for g in candidates if release_kind(g,pid)=='native']
                    # Prefer distinct genres first, then fill remaining sample slots.
                    while candidates and len(selected) < platform_amount:
                        game = next((g for g in candidates if set(x['name'] for x in (g.get('genres') or [])) - genres_seen), candidates[0])
                        candidates.remove(game)
                        selected.append(game)
                        existing.add(game['id'])
                        genres_seen.update(x['name'] for x in (game.get('genres') or []))
                    offset += 100
                for game in selected:
                    save_game(conn, game)
                    conn.execute('INSERT INTO offers(game_id,platform,sale_price,rental_price) VALUES (%s,%s,%s,%s) ON CONFLICT(game_id,platform) DO NOTHING',
                        (game['id'], slug, config.SALE_PRICE, config.RENTAL_PRICE))
                    conn.execute('UPDATE offers SET release_kind=%s WHERE game_id=%s AND platform=%s',(release_kind(game,pid),game['id'],slug))
                    added += 1
            conn.execute("UPDATE import_runs SET status='complete',added=%s,finished_at=now() WHERE id=%s", (added, run_id))
            return {'status': 'complete', 'added': added}
    except IntegrationError as e:
        with connect() as conn:
            conn.execute("UPDATE import_runs SET status='failed',error=%s,added=0,finished_at=now() WHERE id=%s", (str(e), run_id))
        raise
    finally:
        if not client:
            api.close()

def save_game(conn, game):
    cover = (game.get('cover') or {}).get('url')
    if cover:
        cover = 'https:' + cover if cover.startswith('//') else cover
        cover = cover.replace('t_thumb', 't_cover_big')
        if urlparse(cover).hostname != 'images.igdb.com':
            cover = None
    conn.execute('''INSERT INTO games(id,title,summary,cover,genres) VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT(id) DO UPDATE SET title=excluded.title,summary=excluded.summary,cover=excluded.cover,genres=excluded.genres,updated_at=now()''',
        (game['id'], game['name'], game.get('summary') or '', cover, Jsonb([g['name'] for g in (game.get('genres') or [])])))

def catalog(conn, session_id=None, query='', platform='', budget_cents=None, mode='rental'):
    rows = conn.execute('''SELECT o.*,g.title,g.summary,g.cover,g.genres,p.name AS platform_name,
        d.provider AS demo_provider,d.url AS demo_url,d.embed_url
        FROM offers o JOIN games g ON g.id=o.game_id JOIN platforms p ON p.slug=o.platform
        LEFT JOIN demo_links d ON d.offer_id=o.id
        WHERE o.active AND (%s='' OR g.title ILIKE %s) AND (%s='' OR o.platform=%s) ORDER BY p.name,g.title''',
        (query, f'%{query}%', platform, platform)).fetchall()
    for row in rows:
        row['rental_days'] = config.RENTAL_DAYS
        row['sale_available'] = None
        row['rental_available'] = None
        if session_id:
            sale = conn.execute('SELECT quantity FROM sale_stock WHERE session_id=%s AND offer_id=%s', (session_id, row['id'])).fetchone()
            row['sale_available'] = sale['quantity'] if sale else 0
            row['rental_available'] = conn.execute('SELECT count(*) AS n FROM rental_copies WHERE session_id=%s AND offer_id=%s AND available', (session_id, row['id'])).fetchone()['n']
        if row['demo_url'] and not valid_demo_url(row['demo_url']):
            row['demo_url'] = None
            row['embed_url'] = None
        if row['embed_url'] and not valid_demo_url(row['embed_url']):
            row['embed_url'] = None
    if budget_cents is not None:
        rows = [r for r in rows if r['sale_price' if mode == 'sale' else 'rental_price'] <= budget_cents]
    return rows

GAME_FIELDS='id,name,summary,cover.url,genres.name,platforms,game_type.type,parent_game,version_parent,release_dates.platform,release_dates.date'

def release_kind(game,pid):
    kind=(game.get('game_type') or {}).get('type','').lower()
    if kind in {'port','remake','remaster'} or game.get('version_parent'):
        return 'rerelease'
    dates=game.get('release_dates') or []
    target=[r['date'] for r in dates if r.get('platform')==pid and r.get('date') is not None]
    other=[r['date'] for r in dates if r.get('platform')!=pid and r.get('date') is not None]
    if not target: return 'uncertain'
    if other and min(other)<min(target): return 'rerelease'
    if kind=='main game' and not game.get('parent_game'): return 'native'
    return 'uncertain'

def resolve_platform(api,slug):
    from .commerce import DomainError
    if slug not in config.PLATFORMS: raise DomainError('Plataforma inválida.',422)
    rows=api.query('platforms',f'fields id,name; where name={json.dumps(config.PLATFORMS[slug])}; limit 5;')
    exact=[r for r in rows if r.get('name')==config.PLATFORMS[slug]]
    if not exact: raise IntegrationError('Plataforma não encontrada no IGDB.')
    return exact[0]['id']

def search_titles(query,slug,page=0,client=None):
    api=client or IGDB()
    try:
        pid=resolve_platform(api,slug)
        # PSP searches default to earliest PSP launches; rereleases remain selectable.
        search=f'search {json.dumps(query.strip()[:100])};' if query.strip() else 'sort total_rating_count desc;'
        rows=api.query('games',f'fields {GAME_FIELDS}; {search} where platforms=({pid}) & version_parent=null; limit 21; offset {page*20};')
        more=len(rows)>20
        rows=rows[:20]
        for g in rows: g['release_kind']=release_kind(g,pid)
        rows.sort(key=lambda g: {'native':0,'uncertain':1,'rerelease':2}[g['release_kind']])
        return {'results':rows,'page':page,'has_more':more,'platform':slug}
    finally:
        if not client: api.close()

def add_title(game_id,slug,client=None):
    from . import commerce
    api=client or IGDB()
    try:
        pid=resolve_platform(api,slug)
        rows=api.query('games',f'fields {GAME_FIELDS}; where id={int(game_id)}; limit 1;')
        if not rows or pid not in rows[0].get('platforms',[]):
            raise commerce.DomainError('Título incompatível com a plataforma escolhida.',422)
        game=rows[0]
        with connect() as db:
            db.execute('SELECT pg_advisory_xact_lock(172906)')
            db.execute('INSERT INTO platforms VALUES (%s,%s,%s) ON CONFLICT(slug) DO UPDATE SET igdb_id=excluded.igdb_id',(slug,pid,config.LABELS[slug]))
            save_game(db,game)
            offer=db.execute('INSERT INTO offers(game_id,platform,sale_price,rental_price,release_kind) VALUES (%s,%s,%s,%s,%s) ON CONFLICT(game_id,platform) DO NOTHING RETURNING id',(game_id,slug,config.SALE_PRICE,config.RENTAL_PRICE,release_kind(game,pid))).fetchone()
            if not offer:
                old=db.execute('SELECT id FROM offers WHERE game_id=%s AND platform=%s',(game_id,slug)).fetchone()
                return {'offer_id':old['id'],'added':False}
            sessions=db.execute("SELECT id FROM sessions WHERE expired_at IS NULL AND last_seen>now()-(%s * interval '1 second') ORDER BY id FOR UPDATE",(config.SESSION_TTL,)).fetchall()
            for session in sessions: commerce.initialize_offer(db,session['id'],offer['id'])
            return {'offer_id':offer['id'],'added':True}
    finally:
        if not client: api.close()

def review_titles(slug='psp',client=None):
    api=client or IGDB()
    try:
        pid=resolve_platform(api,slug)
        with connect() as db:
            offers=db.execute('SELECT o.*,g.title FROM offers o JOIN games g ON g.id=o.game_id WHERE platform=%s ORDER BY g.title',(slug,)).fetchall()
        if not offers: return []
        games=api.query('games',f'fields {GAME_FIELDS}; where id=({",".join(str(o["game_id"]) for o in offers)}); limit 500;')
        lookup={g['id']:g for g in games}
        for o in offers: o['release_kind']=release_kind(lookup.get(o['game_id'],{}),pid)
        with connect() as db:
            for o in offers: db.execute('UPDATE offers SET release_kind=%s WHERE id=%s',(o['release_kind'],o['id']))
        return offers
    finally:
        if not client: api.close()

def set_offer_active(db,offer_id,active):
    from .commerce import DomainError
    db.execute('SELECT pg_advisory_xact_lock(172906)')
    # Lock sessions in the same order as catalog additions.
    sessions=db.execute('SELECT DISTINCT s.id FROM sessions s JOIN carts c ON c.session_id=s.id WHERE c.offer_id=%s ORDER BY s.id',(offer_id,)).fetchall()
    for s in sessions: db.execute('SELECT id FROM sessions WHERE id=%s FOR UPDATE',(s['id'],))
    offer=db.execute('UPDATE offers SET active=%s WHERE id=%s RETURNING id',(active,offer_id)).fetchone()
    if not offer: raise DomainError('Oferta não encontrada.',404)
    for s in sessions: db.execute('UPDATE sessions SET version=version+1 WHERE id=%s',(s['id'],))
    return {'offer_id':offer_id,'active':active}
