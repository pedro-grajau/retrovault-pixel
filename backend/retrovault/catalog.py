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
                    games = api.query('games', f'fields id,name,summary,cover.url,genres.name; where platforms=({pid}) & version_parent=null; sort total_rating_count desc; limit 100; offset {offset};')
                    if not games:
                        break
                    candidates = [g for g in games if g['id'] not in existing]
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
        WHERE (%s='' OR g.title ILIKE %s) AND (%s='' OR o.platform=%s) ORDER BY p.name,g.title''',
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
